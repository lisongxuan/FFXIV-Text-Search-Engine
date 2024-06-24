from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, func, text, MetaData, Table
import configparser
import datetime

app = Flask(__name__)
api = Api(app)

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.txt')
# 获取数据库配置
db_config = config['database']
host = db_config['host']
port = int(db_config['port'])  # 端口号需要转换为整数
user = db_config['user']
password = db_config['password']
database = db_config['database']
api_config = config['api']
near_range = int(api_config['near_range'])
# Configure your SQLAlchemy database URI here
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'
db = SQLAlchemy(app)

def get_table_name(language, version):
    version_replaced = version.replace('.', '_')
    table_name = f"{language}_{version_replaced}"
    return table_name
class Versions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(255))
    version = db.Column(db.String(255))
    run_date = db.Column(db.DateTime)

def Data(table_name):
    metadata = MetaData()
    metadata.bind = db.engine
    table = Table(table_name, metadata, autoload_with=db.engine)
    metadata.reflect(bind=db.engine)
    return table

class AllVersions(Resource):
    def get(self):
        versions = Versions.query.all()
        return [{'id': v.id, 'language': v.language, 'version': v.version , 'run_date': v.run_date.strftime("%Y-%m-%d %H:%M:%S")} for v in versions]
    
class AllLanguages(Resource):
    def get(self):
        languages = Versions.query.with_entities(Versions.language).distinct()
        return [lang.language for lang in languages]

class VersionsByLanguage(Resource):
    def get(self, language):
        versions = Versions.query.filter_by(language=language).all()
        return [v.version for v in versions]

class LatestVersionByLanguage(Resource):
    def get(self):
        latest_versions = db.session.query(Versions.language, func.max(Versions.version)).group_by(Versions.language).all()
        return [{lang: version} for lang, version in latest_versions]
    


class DataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True)
        parser.add_argument('language', required=True)
        parser.add_argument('version', required=True)
        args = parser.parse_args()
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)
        data = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).all()
        return [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]

class DataByPath(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True)
        parser.add_argument('language', required=True)
        parser.add_argument('version', required=True)
        args = parser.parse_args()
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)
        data = db.session.query(data_table).filter_by(path=args['path']).all()
        if data:
            return [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        else:
            return {'error': 'Data not found'}, 404

class DataAroundPathAndId(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True)
        parser.add_argument('id', required=True, type=int)  # Ensure 'id' is an integer
        parser.add_argument('language', required=True)
        parser.add_argument('version', required=True)
        parser.add_argument('near_range', required=False, type=int)
        args = parser.parse_args()
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)
        data = db.session.query(data_table).filter_by(id=args['id'], path=args['path']).first()
        results = []
        if data:
            data_around = db.session.query(data_table).filter_by(path=args['path']).all()
            data_index = data_around.index(data)
            near_range = args['near_range'] if args['near_range'] else near_range
            start = max(0, data_index - near_range)
            end = data_index + near_range + 1
            results = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data_around[start:end]]
        else:
            results.append({'error': f'Data not found'})
        return results
        
class MultiLanguagesDataByPathAndId(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True)
        parser.add_argument('id', required=True)
        parser.add_argument('languages', required=True)
        parser.add_argument('versions', required=True)
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        results = []
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            data = db.session.query(data_table).filter_by(path=args['path'], id=args['id']).first()
            if data:
                results.append({'language':language,'version':version,'id': data.id, 'name': data.name, 'data': data.data, 'path': data.path})
            else:
                results.append({'error': f'Data not found for language {language} and version {version}'})
        return results

class MultiLanguagesDataAroundPathAndId(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True)
        parser.add_argument('id', type=int, required=True)
        parser.add_argument('languages', required=True)
        parser.add_argument('versions', required=True)
        parser.add_argument('near_range', required=False, type=int)
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        results = []
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            data = db.session.query(data_table).filter_by(path=args['path'], id=args['id']).first()
            if data:
                data_around = db.session.query(data_table).filter_by(path=args['path']).all()
                data_index = data_around.index(data)
                near_range = args['near_range'] if args['near_range'] else near_range
                start = max(0, data_index - near_range)
                end = data_index + near_range + 1
                results.append({'language':language,'version':version,'data':[{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data_around[start:end]]})
            else:
                results.append({'error': f'Data not found for language {language} and version {version}'})
        if not results:
            results.append({'error': f'Data not found for any language and version'})
        
        return results
    

api.add_resource(AllVersions, '/versions')
api.add_resource(AllLanguages, '/languages')
api.add_resource(VersionsByLanguage, '/versions/<string:language>')
api.add_resource(LatestVersionByLanguage, '/latest_versions')
api.add_resource(DataByData, '/data_by_data')
api.add_resource(DataByPath, '/data_by_path')
api.add_resource(DataAroundPathAndId, '/data_around_path_and_id')
api.add_resource(MultiLanguagesDataByPathAndId, '/multi_language_data_by_path_and_id')
api.add_resource(MultiLanguagesDataAroundPathAndId, '/multi_language_data_around_path_and_id')

if __name__ == '__main__':
    app.run(debug=True)