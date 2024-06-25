from flask import Flask,jsonify
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, func, text, MetaData, Table, create_engine, select, union_all, literal, or_
from sqlalchemy.orm import sessionmaker
import configparser
import datetime
from flask_cors import CORS
import re

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
cors=api_config['cors']
app = Flask(__name__)
CORS(app,origins=cors.split(','))
api = Api(app)

# Configure your SQLAlchemy database URI here
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'
db = SQLAlchemy(app)

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

def get_table_name(language, version):
    version_replaced = version.replace('.', '_')
    table_name = f"{language}_{version_replaced}"
    return table_name
def parse_query(query):
    # 解析查询字符串
    tokens = re.findall(r'(-?"[^"]+"|\S+)', query)
    search_terms = {
        "exact": [],
        "exclude": [],
        "language_specific": {},
        "filename": "",
        "expression": ""
    }
    for token in tokens:
        if token.startswith('-"') and token.endswith('"'):
            search_terms["exclude"].append(token[2:-1])
        elif token.startswith('"') and token.endswith('"'):
            search_terms["exact"].append(token[1:-1])
        elif token.startswith('-'):
            search_terms["exclude"].append(token[1:])
        elif ':' in token:
            key, value = token.split(':', 1)
            if key in ["cn", "en", "ja"]:
                if key not in search_terms["language_specific"]:
                    search_terms["language_specific"][key] = []
                search_terms["language_specific"][key].append(value)
            elif key == "filename":
                search_terms["filename"] = value
        elif token.startswith('(') and token.endswith(')'):
            search_terms["expression"] = token[1:-1]
        else:
            search_terms["exact"].append(token)
    return search_terms

def search_data(data, query):
    
    search_terms = parse_query(query)
    results = []
    for item in data:
        # 这里添加具体的搜索逻辑
        pass
    return results

def search_across_tables(data, lang_version_tables):
    queries = []
    for language, version, table_name in lang_version_tables:
        query = text(f"""
            SELECT id, name, data, path, MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE) AS score
            FROM {table_name}
            WHERE MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)
        """)
        query_results = db.session.execute(query, {'data': data}).fetchall()
        
        # Add language and version to each result
        for result in query_results:
            queries.append({
                'id': result[0],
                'name': result[1],
                'data': result[2],
                'path': result[3],
                'score': result[4],
                'language': language,
                'version': version
            })

    # Sort by score in descending order
    queries.sort(key=lambda x: x['score'], reverse=True)
    return queries



class AllVersions(Resource):
    def get(self):
        versions = Versions.query.all()
        return [{'id': v.id, 'language': v.language, 'version': v.version , 'run_date': v.run_date.strftime("%Y-%m-%d %H:%M:%S")} for v in versions]
    
class AllLanguages(Resource):
    def get(self):
        languages = Versions.query.with_entities(Versions.language).distinct()
        return [lang.language for lang in languages]

class VersionsByLanguage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('language', required=True, location='args')
        args = parser.parse_args()
        versions = Versions.query.filter_by(language=args['language']).all()
        return [v.version for v in versions]


class LatestVersionOfLanguage(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('language', required=True, location='args')
        args = parser.parse_args()
        latest_version = db.session.query(
            Versions.language,
            func.max(Versions.version).label('latest_version')
        ).filter_by(language=args['language']).group_by(Versions.language).first()

        if latest_version:
            # Convert the Row object to a dictionary
            result = {
                'language': latest_version.language,
                'latest_version': latest_version.latest_version
            }
            return jsonify(result)  # Use jsonify to return a JSON response
        else:
            return {'message': 'No data found'}, 404
class LatestVersionByLanguage(Resource):
    def get(self):
        latest_versions = db.session.query(Versions.language, func.max(Versions.version)).group_by(Versions.language).all()
        return [{lang: version} for lang, version in latest_versions]

class DataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        # 添加分页参数
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)

        # 计算总数据量
        total = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).count()

        # 修改查询以支持分页
        data = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).paginate(page=args['page'], per_page=args['per_page'], error_out=False).items

        # 返回数据和分页信息
        return {
            'data': [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data],
            'pagination': {
                'page': args['page'],
                'per_page': args['per_page'],
                'total': total,
            }
        }

class MultiDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        # 添加分页参数
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)

        # 优化：一次性查询所有初始数据，并应用分页
        query = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data'])
        total = query.count()  # 计算总数据量
        data = query.paginate(page=args['page'], per_page=args['per_page'], error_out=False).items

        initResults = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        results = []
        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        if not paths_ids:
            return []  # Or return a meaningful message
        # 构建查询映射
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 一次性查询所有相关数据
            all_data = db.session.query(data_table).filter(
    text("path IN :paths AND id IN :ids")
).params(
    paths=[path for path, _ in paths_ids],
    ids=[id for _, id in paths_ids]
).all()
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [{'language': language, 'version': version, 'data': f'Data not found for language {language} and version {version}'} for language, version in zip(languages, versions)])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})

        return {
            'data': results,
            'pagination': {
                'page': args['page'],
                'per_page': args['per_page'],
                'total': total,
            }
        }
    
class MultiLanguagesDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        # 添加分页参数
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]
        initresults = search_across_tables(args['data'], lang_version_tables)

        # 分页处理
        page = args['page']
        per_page = args['per_page']
        start = (page - 1) * per_page
        end = start + per_page
        paginated_initresults = initresults[start:end]

        results = []
        paths_ids = set((initresult['path'], initresult['id']) for initresult in paginated_initresults)
        if not paths_ids:
            return {'data': [], 'pagination': {'page': page, 'per_page': per_page, 'total': len(initresults)}}

        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            all_data = db.session.query(data_table).filter(
                text("path IN :paths AND id IN :ids")
            ).params(
                paths=[path for path, _ in paths_ids],
                ids=[id for _, id in paths_ids]
            ).all()
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})

        for initresult in paginated_initresults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': result_data, 'path': initresult['path']})

        return {
            'data': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': len(initresults),
            }
        }


class IncludeMultiDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        table = Data(table_name)

        # 分页查询
        stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data.like(f"%{args['data']}%"))
        subquery = stmt.subquery()  # Create a subquery and alias it
        total_query = db.session.execute(select(db.func.count()).select_from(subquery)).scalar()  # Corrected usage
        data = db.session.execute(stmt.limit(args['per_page']).offset((args['page'] - 1) * args['per_page'])).fetchall()
        initResults = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]

        if not initResults:
            return {'data': [], 'pagination': {'page': args['page'], 'per_page': args['per_page'], 'total': total_query}}

        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            all_data = db.session.query(data_table).filter(
                text("path IN :paths AND id IN :ids")
            ).params(
                paths=[path for path, _ in paths_ids],
                ids=[id for _, id in paths_ids]
            ).all()
            for data in all_data:
                key = (data.path, data.id)
                data_mapping.setdefault(key, []).append({'language': language, 'version': version, 'data': data.data})

        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': result_data, 'path': initresult['path']})

        return {
            'data': results,
            'pagination': {
                'page': args['page'],
                'per_page': args['per_page'],
                'total': total_query
            }
        }
   
class ExactMultiDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('page', type=int, required=False, default=1, location='args')  # 分页参数
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')  # 分页参数
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        table = Data(table_name)

        # 分页查询
        stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data == f"{args['data']}")
        subquery = stmt.subquery()  # 创建子查询并给它一个别名
        total_query = db.session.execute(select(db.func.count()).select_from(subquery)).scalar()  # 正确的使用方式
        data = db.session.execute(stmt.limit(args['per_page']).offset((args['page'] - 1) * args['per_page'])).fetchall()
        initResults = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]

        if not initResults:
            return {'data': [], 'pagination': {'page': args['page'], 'per_page': args['per_page'], 'total': total_query}}

        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            all_data = db.session.query(data_table).filter(
                text("path IN :paths AND id IN :ids")
            ).params(
                paths=[path for path, _ in paths_ids],
                ids=[id for _, id in paths_ids]
            ).all()
            for data in all_data:
                key = (data.path, data.id)
                data_mapping.setdefault(key, []).append({'language': language, 'version': version, 'data': data.data})

        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'path': initresult['path'], 'data': result_data})

        return {
            'data': results,
            'pagination': {
                'page': args['page'],
                'per_page': args['per_page'],
                'total': total_query
            }
        }

def include_search_across_tables(data, lang_version_tables, page=1, per_page=10):
    total_count = 0
    queries = []

    # 首先计算总记录数
    for language, version, table_name in lang_version_tables:
        table = Data(table_name)
        count_stmt = select(func.count()).select_from(table).where(table.c.data.like(f"%{data}%"))
        total_count += db.session.execute(count_stmt).scalar()

    total_pages = (total_count + per_page - 1) // per_page

    # 确定从哪个表格开始查询和跳过多少条记录
    items_to_skip = (page - 1) * per_page
    items_collected = 0

    for language, version, table_name in lang_version_tables:
        if items_collected >= per_page:
            break  # 已收集到足够的条目

        table = Data(table_name)
        if items_to_skip > 0:
            # 计算当前表格的记录数
            count_stmt = select(func.count()).select_from(table).where(table.c.data.like(f"%{data}%"))
            table_count = db.session.execute(count_stmt).scalar()

            if items_to_skip >= table_count:
                # 如果需要跳过的条目数大于当前表格的记录数，则跳过这个表格
                items_to_skip -= table_count
                continue
            else:
                # 调整查询以跳过部分记录
                stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data.like(f"%{data}%")).limit(per_page - items_collected).offset(items_to_skip)
                items_to_skip = 0  # 重置跳过的条目数，因为已经开始收集数据
        else:
            stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data.like(f"%{data}%")).limit(per_page - items_collected)

        query_results = db.session.execute(stmt).fetchall()

        for result in query_results:
            queries.append({
                'id': result.id,
                'name': result.name,
                'data': result.data,
                'path': result.path,
                'language': language,
                'version': version
            })
            items_collected += 1
            if items_collected >= per_page:
                break  # 已收集到足够的条目

    pagination_info = {
        'total': total_count,
        'page': page,
        'per_page': per_page
    }

    return {
        'data': queries,
        'pagination': pagination_info
    }
class IncludeMultiLanguagesDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        # 解析分页参数
        parser.add_argument('page', type=int, location='args', default=1)
        parser.add_argument('per_page', type=int, location='args', default=10)
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]

        # 传递分页参数
        search_results = include_search_across_tables(args['data'], lang_version_tables, args['page'], args['per_page'])
        if not search_results['data']:
            return {'message': 'No data found for the given parameters', 'data': [], 'pagination': search_results['pagination']}

        paths_ids = set((result['path'], result['id']) for result in search_results['data'])
        data_mapping = {}

        # 构建查询条件
        conditions = [text(f"path = :path_{i} AND id = :id_{i}") for i, _ in enumerate(paths_ids)]
        parameters = {**{f"path_{i}": path for i, (path, _) in enumerate(paths_ids)}, **{f"id_{i}": id for i, (_, id) in enumerate(paths_ids)}}

        # 一次性查询所有相关数据
        union_query = union_all(*[
            select(*[literal(language).label('language'), literal(version).label('version'), data_table.c.data, data_table.c.path, data_table.c.id])
            for language, version, table_name in lang_version_tables
            for data_table in [Data(table_name)]
        ])
        subquery = union_query.subquery()
        all_data_query = select(subquery).where(or_(*conditions))
        all_data = db.session.execute(all_data_query, parameters).fetchall()

        # 将查询结果存储在映射中
        for data in all_data:
            key = (data.path, data.id)
            data_mapping.setdefault(key, []).append({'language': data.language, 'version': data.version, 'data': data.data})

        # 使用映射填充结果
        results = []
        for initresult in search_results['data']:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'path': initresult['path'], 'data': result_data})

        return {'data': results, 'pagination': search_results['pagination']}
 
def exact_search_across_tables(data, lang_version_tables, page=1, per_page=10):
    total_count = 0
    queries = []

    # 首先计算总记录数
    for language, version, table_name in lang_version_tables:
        table = Data(table_name)
        count_stmt = select(func.count()).select_from(table).where(table.c.data == f"{data}")
        total_count += db.session.execute(count_stmt).scalar()

    total_pages = (total_count + per_page - 1) // per_page

    # 确定从哪个表格开始查询和跳过多少条记录
    items_to_skip = (page - 1) * per_page
    items_collected = 0

    for language, version, table_name in lang_version_tables:
        if items_collected >= per_page:
            break  # 已收集到足够的条目

        table = Data(table_name)
        if items_to_skip > 0:
            # 计算当前表格的记录数
            count_stmt = select(func.count()).select_from(table).where(table.c.data == f"{data}")
            table_count = db.session.execute(count_stmt).scalar()

            if items_to_skip >= table_count:
                # 如果需要跳过的条目数大于当前表格的记录数，则跳过这个表格
                items_to_skip -= table_count
                continue
            else:
                # 调整查询以跳过部分记录
                stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data == f"{data}").limit(per_page - items_collected).offset(items_to_skip)
                items_to_skip = 0  # 重置跳过的条目数，因为已经开始收集数据
        else:
            stmt = select(table.c.id, table.c.name, table.c.data, table.c.path).where(table.c.data == f"{data}").limit(per_page - items_collected)

        query_results = db.session.execute(stmt).fetchall()

        for result in query_results:
            queries.append({
                'id': result.id,
                'name': result.name,
                'data': result.data,
                'path': result.path,
                'language': language,
                'version': version
            })
            items_collected += 1
            if items_collected >= per_page:
                break  # 已收集到足够的条目

    pagination_info = {
        'total': total_count,
        'page': page,
        'per_page': per_page
    }

    return {
        'data': queries,
        'pagination': pagination_info
    }
   
class ExactMultiLanguagesDataByData(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('page', type=int, location='args', default=1)
        parser.add_argument('per_page', type=int, location='args', default=10)
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]

        search_results = exact_search_across_tables(args['data'], lang_version_tables, args['page'], args['per_page'])
        if not search_results['data']:
            return {'message': 'No data found for the given parameters', 'data': [], 'pagination': search_results['pagination']}

        paths_ids = set((result['path'], result['id']) for result in search_results['data'])
        data_mapping = {}

        conditions = [text(f"path = :path_{i} AND id = :id_{i}") for i, _ in enumerate(paths_ids)]
        parameters = {**{f"path_{i}": path for i, (path, _) in enumerate(paths_ids)}, **{f"id_{i}": id for i, (_, id) in enumerate(paths_ids)}}

        union_query = union_all(*[
            select(*[literal(language).label('language'), literal(version).label('version'), data_table.c.data, data_table.c.path, data_table.c.id])
            for language, version, table_name in lang_version_tables
            for data_table in [Data(table_name)]
        ])
        subquery = union_query.subquery()
        all_data_query = select(subquery).where(or_(*conditions))
        all_data = db.session.execute(all_data_query, parameters).fetchall()

        for data in all_data:
            key = (data.path, data.id)
            data_mapping.setdefault(key, []).append({'language': data.language, 'version': data.version, 'data': data.data})

        results = []
        for initresult in search_results['data']:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'],  'path': initresult['path'], 'data': result_data})

        return {'data': results, 'pagination': search_results['pagination']}
    
class DataByPath(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('path', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
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
        parser.add_argument('path', required=True, location='args')
        parser.add_argument('id', required=True, type=int, location='args')  # Ensure 'id' is an integer
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('near_range', required=False, type=int, location='args')
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
        parser.add_argument('path', required=True, location='args')
        parser.add_argument('id', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
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

class MultiLanguagesDataAroundName(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('near_range', required=False, type=int, location='args')
        args = parser.parse_args()
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        results = []
        print(near_range)
        nearrange = args['near_range'] if args['near_range'] else near_range
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            data = db.session.query(data_table).filter_by(name=args['name']).first()
            if data:
                start_index = max(0, data.id - nearrange)
                end_index = data.id + nearrange

                sql_query = text(f"""
SELECT * FROM (
    SELECT *
    FROM {table_name}
    WHERE path = :path
) AS numbered_rows
WHERE id BETWEEN :start_index AND :end_index
""")

                data_around = db.session.execute(sql_query, {'path': data.path, 'start_index': start_index, 'end_index': end_index}).fetchall()
                results.append({'language':language,'version':version,'data':[{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data_around]})
            else:
                results.append({'error': f'Data not found for language {language} and version {version}'})
        if not results:
            results.append({'error': f'Data not found for any language and version'})
        results_by_id = {}
        for entry in results:
            if 'error' in entry:
                continue
            language = entry['language']
            version = entry['version']
            for data_item in entry['data']:
                item_id = data_item['id']
                if item_id not in results_by_id:
                    results_by_id[item_id] = {
                        'id': item_id,
                        'name': data_item['name'],
                        'data': [],
                        'path': data_item['path']
                    }
                results_by_id[item_id]['data'].append({
                    'language': language,
                    'version': version,
                    'data': data_item['data']
                })
        resultList = list(results_by_id.values())
        return {'data': resultList, 'pagination': {
                'page': 1,
                'per_page': len(resultList),
                'total': len(resultList),
            }}
        return list(results_by_id.values())
    

api.add_resource(AllVersions, '/versions')
api.add_resource(AllLanguages, '/languages')
api.add_resource(VersionsByLanguage, '/versions/<string:language>')
api.add_resource(LatestVersionOfLanguage, '/latest_version')
api.add_resource(LatestVersionByLanguage, '/latest_versions')
api.add_resource(DataByData, '/data_by_data')
api.add_resource(MultiDataByData, '/multi_data_by_data')
api.add_resource(MultiLanguagesDataByData, '/multi_language_data_by_data')
api.add_resource(IncludeMultiDataByData, '/include_multi_data_by_data')
api.add_resource(IncludeMultiLanguagesDataByData, '/include_multi_language_data_by_data')
api.add_resource(ExactMultiDataByData, '/exact_multi_data_by_data')
api.add_resource(ExactMultiLanguagesDataByData, '/exact_multi_language_data_by_data')
api.add_resource(DataByPath, '/data_by_path')
api.add_resource(DataAroundPathAndId, '/data_around_path_and_id')
api.add_resource(MultiLanguagesDataByPathAndId, '/multi_language_data_by_path_and_id')
api.add_resource(MultiLanguagesDataAroundName, '/multi_language_data_around_name')

if __name__ == '__main__':
    app.run(debug=True)
