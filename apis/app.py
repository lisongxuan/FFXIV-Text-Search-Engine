from flask import Flask,jsonify
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import desc, func, text, MetaData, Table, create_engine, select, union_all, literal, or_
from sqlalchemy.orm import sessionmaker
import configparser
import datetime
from flask_cors import CORS
import re
from flask_caching import Cache


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
CORS(app)
api = Api(app)
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'
app.config['SQLALCHEMY_POOL_RECYCLE'] = 1800
app.config['SQLALCHEMY_POOL_PRE_PING'] = True
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
db = SQLAlchemy(app)
Base = declarative_base()

def Data(table_name):
    class DynamicDataModel(Base):
        __tablename__ = table_name
        __table_args__ = {'extend_existing': True}  
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String)
        data = db.Column(db.String)
        path = db.Column(db.String, primary_key=True)
    return DynamicDataModel

class Versions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(255))
    version = db.Column(db.String(255))
    run_date = db.Column(db.DateTime)



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

def search_across_tables_paginated(data, lang_version_tables, page, per_page):
    all_results = []
    total = 0
    for language, version, table_name in lang_version_tables:
        query = text(f"""
            SELECT id, name, data, path, MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE) AS score
            FROM {table_name}
            WHERE MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT :limit OFFSET :offset
        """)
        # 计算分页参数
        limit = per_page
        offset = (page - 1) * per_page
        query_results = db.session.execute(query, {'data': data, 'limit': limit, 'offset': offset}).fetchall()
      
        # 为每个结果添加语言和版本信息
        for result in query_results:
            all_results.append({
                'id': result[0],
                'name': result[1],
                'data': result[2],
                'path': result[3],
                'score': result[4],
                'language': language,
                'version': version
            })
      
        # 更新总数，假设每个表的数据量相同，这里简化处理
        if total == 0:
            total_query = text(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)
            """)
            total_result = db.session.execute(total_query, {'data': data}).fetchone()
            total = total_result[0]

    db.session.close()

    # 不需要再次排序，因为每个查询已经按score降序排序
    return all_results, total



class AllVersions(Resource):
    @cache.cached(timeout=3600)  
    def get(self):
        print(datetime.datetime.now())
        versions = Versions.query.all()
        print(datetime.datetime.now())
        return [{'id': v.id, 'language': v.language, 'version': v.version , 'run_date': v.run_date.strftime("%Y-%m-%d %H:%M:%S")} for v in versions]
  
 
class AllLanguages(Resource):
    @cache.cached(timeout=3600)   
    def get(self):
        languages = Versions.query.with_entities(Versions.language).distinct()
        return [lang.language for lang in languages]
class VersionsByLanguage(Resource):
    @cache.cached(timeout=3600)   
    def get(self, language):
        versions = Versions.query.filter_by(language=language).all()
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
        db.session.close()
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
        db.session.close()
        return [{lang: version} for lang, version in latest_versions]

class DataByData(Resource):
    def get(self):
        print(datetime.datetime.now())
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
        total = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE) ")).params(data=args['data']).count()

        # 修改查询以支持分页
        data = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data']).paginate(page=args['page'], per_page=args['per_page'], error_out=False).items
        db.session.close()
        print(datetime.datetime.now())
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
        print(datetime.datetime.now())
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('language', required=True, location='args')
        parser.add_argument('version', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        # 分页参数保持不变
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        table_name = get_table_name(args['language'], args['version'])
        data_table = Data(table_name)

        # 优化：只查询当前页的数据
        query = db.session.query(data_table).filter(text("MATCH (data) AGAINST (:data IN NATURAL LANGUAGE MODE)")).params(data=args['data'])
        total = query.count()  # 计算总数据量
        data = query.offset((args['page'] - 1) * args['per_page']).limit(args['per_page']).all()

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
            # 优化：只查询当前页相关的数据
            for attr in dir(data_table):
                try:
                    print("data_table.%s = %r" % (attr, getattr(data_table, attr)))
                except (AttributeError, NotImplementedError):
                    print("data_table.%s is not accessible or not implemented" % attr)
            all_data = db.session.query(data_table).filter(
                data_table.path.in_([path for path, _ in paths_ids]),
                data_table.id.in_([id for _, id in paths_ids])
            ).all()
          
            # 将查询结果存储在映射中
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})
        db.session.close()

        # 使用映射填充结果
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': initresult['data'], 'path': initresult['path'], 'data': result_data})
        print(datetime.datetime.now())
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
        print(datetime.datetime.now())
        parser = reqparse.RequestParser()
        parser.add_argument('data', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('page', type=int, required=False, default=1, location='args')
        parser.add_argument('per_page', type=int, required=False, default=10, location='args')
        args = parser.parse_args()

        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]

        # 优化：直接在数据库层面进行分页处理，避免先加载所有数据到内存
        # 假设search_across_tables函数已经被优化为支持分页
        paginated_initresults, total = search_across_tables_paginated(args['data'], lang_version_tables, args['page'], args['per_page'])

        results = []
        paths_ids = set((initresult['path'], initresult['id']) for initresult in paginated_initresults)
        if not paths_ids:
            return {'data': [], 'pagination': {'page': args['page'], 'per_page': args['per_page'], 'total': total}}
        print(datetime.datetime.now())
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 优化：使用更有效的查询条件
            all_data = db.session.query(data_table).filter(
                data_table.path.in_([path for path, _ in paths_ids]),
                data_table.id.in_([id for _, id in paths_ids])
            ).all()
          
            for data in all_data:
                key = (data.path, data.id)
                if key not in data_mapping:
                    data_mapping[key] = []
                data_mapping[key].append({'language': language, 'version': version, 'data': data.data})
        db.session.close()
        print(datetime.datetime.now())
        for initresult in paginated_initresults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'data': result_data, 'path': initresult['path']})
        print(datetime.datetime.now())
        return {
            'data': results,
            'pagination': {
                'page': args['page'],
                'per_page': args['per_page'],
                'total': total,
            }
        }


class IncludeMultiDataByData(Resource):
    def get(self):
        print(datetime.datetime.now())
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

        # 优化分页查询
        stmt = select(table.id, table.name, table.data, table.path).where(table.data.like(f"%{args['data']}%"))
        total_query = db.session.execute(select(db.func.count()).select_from(stmt.subquery())).scalar()
        print(datetime.datetime.now())
        data = db.session.execute(stmt.limit(args['per_page']).offset((args['page'] - 1) * args['per_page'])).fetchall()
        print(datetime.datetime.now())
        initResults = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]

        if not initResults:
            return {'data': [], 'pagination': {'page': args['page'], 'per_page': args['per_page'], 'total': total_query}}

        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        paths, ids = zip(*paths_ids)  # 解包paths和ids
        data_mapping = {}
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            # 优化数据检索
            all_data = db.session.query(data_table).filter(
                data_table.path.in_(paths),
                data_table.id.in_(ids)
            ).all()
          
            for data in all_data:
                key = (data.path, data.id)
                data_mapping.setdefault(key, []).append({'language': language, 'version': version, 'data': data.data})
        print(datetime.datetime.now())
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
        print(datetime.datetime.now())
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

        # 分页查询优化
        stmt = select(table.id, table.name, table.data, table.path).where(table.data == args['data'])
        total_query = db.session.execute(select(func.count()).select_from(stmt.subquery())).scalar()
        data = db.session.execute(stmt.limit(args['per_page']).offset((args['page'] - 1) * args['per_page'])).fetchall()
        initResults = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data]
        print(datetime.datetime.now())
        if not initResults:
            return {'data': [], 'pagination': {'page': args['page'], 'per_page': args['per_page'], 'total': total_query}}

        paths_ids = set((initresult['path'], initresult['id']) for initresult in initResults)
        paths, ids = zip(*paths_ids)  # 解包paths和ids
        data_mapping = {}
        print(datetime.datetime.now())
        # 优化数据检索
        for language, version in zip(languages, versions):
            table_name = get_table_name(language, version)
            data_table = Data(table_name)
            stmt = select(data_table.id, data_table.data, data_table.path).where(
                data_table.path.in_(paths),
                data_table.id.in_(ids)
            )
            all_data = db.session.execute(stmt).fetchall()

            for d in all_data:
                key = (d.path, d.id)
                data_mapping.setdefault(key, []).append({'language': language, 'version': version, 'data': d.data})
        print(datetime.datetime.now())
        results = []
        for initresult in initResults:
            key = (initresult['path'], initresult['id'])
            result_data = data_mapping.get(key, [])
            results.append({'id': initresult['id'], 'name': initresult['name'], 'path': initresult['path'], 'data': result_data})

        db.session.close()
        print(datetime.datetime.now())
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
    print(datetime.datetime.now())
    # 首先计算总记录数
    for language, version, table_name in lang_version_tables:
        table = Data(table_name)
        count_stmt = select(func.count()).select_from(table).where(table.data.like(f"%{data}%"))
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
            count_stmt = select(func.count()).select_from(table).where(table.data.like(f"%{data}%"))
            table_count = db.session.execute(count_stmt).scalar()

            if items_to_skip >= table_count:
                # 如果需要跳过的条目数大于当前表格的记录数，则跳过这个表格
                items_to_skip -= table_count
                continue
            else:
                # 调整查询以跳过部分记录
                stmt = select(table.id, table.name, table.data, table.path).where(table.data.like(f"%{data}%")).limit(per_page - items_collected).offset(items_to_skip)
                items_to_skip = 0  # 重置跳过的条目数，因为已经开始收集数据
        else:
            stmt = select(table.id, table.name, table.data, table.path).where(table.data.like(f"%{data}%")).limit(per_page - items_collected)

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
    print(datetime.datetime.now())
    return {
        'data': queries,
        'pagination': pagination_info
    }
class IncludeMultiLanguagesDataByData(Resource):
    def get(self):
        print(datetime.datetime.now())
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
        print(datetime.datetime.now())
        # 一次性查询所有相关数据
        union_query = union_all(*[
            select(*[literal(language).label('language'), literal(version).label('version'), data_table.data, data_table.path, data_table.id])
            for language, version, table_name in lang_version_tables
            for data_table in [Data(table_name)]
        ])
        subquery = union_query.subquery()
        all_data_query = select(subquery).where(or_(*conditions))
        all_data = db.session.execute(all_data_query, parameters).fetchall()
        print(datetime.datetime.now())
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
        print(datetime.datetime.now())
        return {'data': results, 'pagination': search_results['pagination']}
 
def exact_search_across_tables(data, lang_version_tables, page=1, per_page=10):
    total_count = 0
    queries = []
    print(datetime.datetime.now())
    # 首先计算总记录数
    for language, version, table_name in lang_version_tables:
        table = Data(table_name)
        count_stmt = select(func.count()).select_from(table).where(table.data == f"{data}")
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
            count_stmt = select(func.count()).select_from(table).where(table.data == f"{data}")
            table_count = db.session.execute(count_stmt).scalar()

            if items_to_skip >= table_count:
                # 如果需要跳过的条目数大于当前表格的记录数，则跳过这个表格
                items_to_skip -= table_count
                continue
            else:
                # 调整查询以跳过部分记录
                stmt = select(table.id, table.name, table.data, table.path).where(table.data == f"{data}").limit(per_page - items_collected).offset(items_to_skip)
                items_to_skip = 0  # 重置跳过的条目数，因为已经开始收集数据
        else:
            stmt = select(table.id, table.name, table.data, table.path).where(table.data == f"{data}").limit(per_page - items_collected)

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
    print(datetime.datetime.now())
    return {
        'data': queries,
        'pagination': pagination_info
    }
   
class ExactMultiLanguagesDataByData(Resource):
    def get(self):
        print(datetime.datetime.now())
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
        print(datetime.datetime.now())
        union_query = union_all(*[
            select(*[literal(language).label('language'), literal(version).label('version'), data_table.data, data_table.path, data_table.id])
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
        print(datetime.datetime.now())
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
        db.session.close()
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

        if data_table is None:
            return {'error': f"Invalid language/version: {args['language']}/{args['version']}"}, 404
        data = db.session.query(data_table).filter_by(id=args['id'], path=args['path']).first()
        results = []
        if data:
            data_around = db.session.query(data_table).filter_by(path=args['path']).all()
            data_index = data_around.index(data)
            nearrange = args['near_range'] if args['near_range'] else near_range
            start = max(0, data_index - nearrange)
            end = data_index + nearrange + 1
            results = [{'id': d.id, 'name': d.name, 'data': d.data, 'path': d.path} for d in data_around[start:end]]
        else:
            results.append({'error': f'Data not found'})
        db.session.close()
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
        db.session.close()
        return results

class MultiLanguagesDataAroundName(Resource):
    def get(self):
        print(datetime.datetime.now())
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, location='args')
        parser.add_argument('languages', required=True, location='args')
        parser.add_argument('versions', required=True, location='args')
        parser.add_argument('near_range', required=False, type=int, location='args', default=10)
        args = parser.parse_args()
      
        languages = args['languages'].split(',')
        versions = args['versions'].split(',')
        near_range = args['near_range']
        lang_version_tables = [(language, version, get_table_name(language, version)) for language, version in zip(languages, versions)]
        results = []
        data_mapping = {}
        path_id_pairs = []
        print(datetime.datetime.now())
        # 构建联合查询来查找数据
        union_query = union_all(*[
            select(*[literal(language).label('language'), literal(version).label('version'), data_table.data, data_table.path, data_table.id])
            .where(Data(table_name).name == args['name'])
            for language, version, table_name in lang_version_tables
            for data_table in [Data(table_name)]
        ])

        # 执行查询并收集结果
        query_results = db.session.execute(union_query).fetchall()
        print(datetime.datetime.now())
        for result in query_results:
            if result:
                language = result.language
                version = result.version
                path_id_pairs.append((result.path, result.id))
                near_range = args['near_range'] if args['near_range'] is not None else near_range
                start_index = max(0, result.id - near_range)
                end_index = result.id + near_range

                sql_query = text(f"""
                    SELECT * FROM {get_table_name(language, version)}
                    WHERE path = :path AND id BETWEEN :start_index AND :end_index
                """)
                data_around = db.session.execute(sql_query, {'path': result.path, 'start_index': start_index, 'end_index': end_index}).fetchall()
              
                for d in data_around:
                    key = (d.path, d.id)
                    if key not in data_mapping:
                        data_mapping[key] = {
                            'id': d.id,
                            'name': d.name,
                            'path': d.path,
                            'data': []
                        }
                    data_mapping[key]['data'].append({
                        'language': language,
                        'version': version,
                        'data': d.data
                    })
            else:
                results.append({'error': f'Data not found for language {language} and version {version}'})
      
        db.session.close()
        print(datetime.datetime.now())
        resultList = list(data_mapping.values())
      
        return {
            'data': resultList,
            'pagination': {
                'page': 1,
                'per_page': len(resultList),
                'total': len(resultList),
            }
        }

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

