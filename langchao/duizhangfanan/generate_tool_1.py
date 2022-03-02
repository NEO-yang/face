# -*- coding: utf-8 -*-
"""
==================================================
@创建人 ：杨兴财
@当前维护人 ：杨兴财
@Desc ：会计中心对账方案工具
==================================================
"""
import string
import random
from lxml import etree
from lxml.builder import E


FIELDS_TO_EXPORT = {
    # 主表：业务单据对账方案设置
    'acc.center.reconciliation.scheme': ['name', 'state', 'acct_book_id', 'acct_org_id', 'business_module', 'line1_ids', 'description'],
    # 一级子表：业务单据对账方案设置-总账设置
    'acc.center.reconciliation.scheme.line1': ['account_id', 'acct_book_id', 'biz_doc_setting', 'biz_line_ids',
        'dimension_id', 'gl_decrease_field_id', 'gl_increase_field_id', 'sequence'],
    # 二级子表：业务单据对账方案设置-业务单据设置
    'acc.center.reconciliation.scheme.line1.line2': ['biz_data_type', 'condition_id', 'curr_field_id', 'd_corr_doc_field_id', 
        'd_corr_filed_model_id', 'description','doc_date_field_id', 'doc_field_id', 'doc_filed_model_id', 'model_id', 'sequence', 'sett_org_field_id'],
    # 对账单据过滤规则
    'acc.center.rs.condition.setting': ['name', 'model_id', 'filter_domain', 'is_doc_condition'],
}


# 参考odoo web_studio: controllers/export.py中xmlid_getter方法
def xmlid_getter():
    """ Return a function that returns the xml_id of a given record. """
    cache = {}

    def get(record, random_number=None, source_doc_model=None):
        """ Return the xml_id of ``record``.
            Raise a ``MissingXMLID`` if ``check`` is true and xml_id is empty.
        """
        if record not in cache:
            # prefetch when possible
            records = record.browse(record._prefetch_ids)
            for rid, val in records.get_external_id().items():
                if val:
                    cache[record.browse(rid)] = val
        if record not in cache and record._name in FIELDS_TO_EXPORT:
            if source_doc_model:
                cache[record] = '__'.join([source_doc_model.replace('.', '_'), record._name.replace('.', '_'), str(record.id)])
            else:
                cache[record] = '__'.join([record._name.replace('.', '_'), random_number, str(record.id)])
        return cache.get(record, None)

    return get


def get_field_node(field, value, get_xmlid):
    """
    根据不同类型的字段，生成字段节点
    @param field: 字段对象
    @param value: 字段值
    @param source_doc_model: 来源单据模型
    @param get_xmlid: 获取record id的对象，内含缓存
    @return field的xml节点
    """
    if field.type == 'boolean':
        return E.field(name=field.name, eval=str(value))
    elif field.type in ('many2one', 'many2many', 'one2many'):
        if field.comodel_name == 'ir.model':
            # 根据值的数量，修改search里的内容
            opt, model_str = ('=', "'%s'" % value.model) if len(value) == 1 else ('in', '[%s]' % ', '.join("'%s'" % v.model for v in value))
            return E.field(name=field.name, search="[('model', '%s', %s)]" % (opt, model_str))
        elif field.comodel_name == 'ir.model.fields':
            if len(value) == 1:
                model_str, opt, field_str = (value.model, '=', "'%s'" % value.name) 
            else:
                # TODO: 目前都是同一个模型下的不同字段，如果后期出现不同模型下的不同字段，就需要通过`|`去分割生成domain
                model_str, opt, field_str = (value[0].model, 'in', '[%s]' % ', '.join("'%s'" % v.name for v in value)) 
            return E.field(name=field.name, search="[('model', '=', '%s'), ('name', '%s', %s)]" % (model_str, opt, field_str))
        elif field.type == 'many2one':
            return E.field(name=field.name, ref=get_xmlid(value))
        elif field.type in ('many2many', 'one2many'):
            refs = []
            for v in value:
                xml_id = get_xmlid(v)
                if xml_id:
                    refs.append("ref('%s')" % xml_id)
            return E.field(name=field.name, eval='[(6, 0, [%s])]' % ', '.join(refs))
    else:
        return E.field(str(value), name=field.name)


def get_records_nodes(records, get_xmlid, random_number=None, source_doc_model=None):
    """
    根据records记录，获取records节点
    @param records: 记录集
    @param source_doc_model: 来源单据模型
    @param get_xmlid: 获取record id的对象，内含缓存
    @return record xml节点列表
    """
    fields = records[0]._fields
    nodes = []
    for record in records:
        # 获取record_id, 创建一个record节点
        xmlid = get_xmlid(record, random_number, source_doc_model)
        record_node = E.record(id=xmlid, model=record._name)
        for field_name in FIELDS_TO_EXPORT.get(record._name, []):
            value = record[field_name] if hasattr(record, field_name) else None
            # 生成field节点，并添加到record节点中
            if value:
                record_node.append(get_field_node(fields.get(field_name, None), value, get_xmlid))
            nodes.append(record_node)
    return nodes


def generate(templates):
    """
    根据凭证模板记录生成对应结构的数据树
    """
    get_xmlid = xmlid_getter()
    random_str = random.sample(string.digits, k=6)
    random_number = ("".join(random_str))
    record_nodes = [] # 导出的全部record节点
    for template in templates:
        # 获取模板方案的配置数据
        lines = template.line1_ids  # 一级子表明细行
        account_id = lines.account_id
        dimension_id = lines.dimension_id
        gl_decrease_field_id = lines.gl_decrease_field_id
        gl_increase_field_id = lines.gl_increase_field_id
        for biz_line_ids in lines.biz_line_ids:
            model_id = biz_line_ids.model_id
            source_doc_model = model_id.model
            d_corr_doc_field_id = biz_line_ids.d_corr_doc_field_id
            d_corr_filed_model_id = biz_line_ids.d_corr_filed_model_id
            condition_id = biz_line_ids.condition_id
            doc_filed_model_id = biz_line_ids.doc_filed_model_id
            doc_field_id = biz_line_ids.doc_field_id
            doc_date_field_id = biz_line_ids.doc_date_field_id
            curr_field_id = biz_line_ids.curr_field_id
            sett_org_field_id = biz_line_ids.sett_org_field_id

            # 按顺序导出，确保加载时不会报错
            for records in (sett_org_field_id, curr_field_id, doc_date_field_id, doc_field_id, doc_filed_model_id, condition_id, 
                    d_corr_filed_model_id, d_corr_doc_field_id, model_id, biz_line_ids):
                if records:
                    record_nodes.extend(get_records_nodes(records, get_xmlid, source_doc_model=source_doc_model))
        for records in (gl_increase_field_id, gl_decrease_field_id, dimension_id, account_id, lines, template):
            if records:
                record_nodes.extend(get_records_nodes(records, get_xmlid, random_number=random_number))

    return etree.tostring(E.odoo(E.data(noupdate='1', *record_nodes)), encoding="utf-8", pretty_print=True, xml_declaration=True)