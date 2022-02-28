# -*- coding: utf-8 -*-
"""
==================================================
@创建人 ：Vic Sun
@当前维护人 ： Vic Sun
@Desc ：会计中心凭证方案预置数据生成器
==================================================
"""
from lxml import etree
from lxml.builder import E


FIELDS_TO_EXPORT = {
    'acc.center.template.account.condition.setting': ['name', 'model_id', 'filter_domain'],
    'acc.center.template.auxiliary.setting': ['dimension_id', 'method', 'fixed_value', 'source_field_id', 'source_doc_id'],
    'acc.center.template.account.setting.line1': [
        'account_condition_id', 'account_id', 'cash_flow_main_id', 'cash_flow_sch_id', 'auxiliary_set_ids', 'source_doc_id'
    ],
    'acc.center.template.account.setting': ['name', 'line_ids', 'source_doc_id', 'acct_book_id', 'acct_table_id'],
    'acc.center.template.summary': ['name', 'source_doc_id', 'source_doc_fields', 'summary'],
    'acc.center.template.condition.setting': ['name', 'model_id', 'filter_domain'],
    'acc.center.template.line1': [
        'sequence', 'condition_id', 'summary_id', 'account_setting_id', 'direction', 'curr_field_id', 
        'curr_rate_field_id', 'amount_field_id', 'standard_amount_field_id'
    ],
    'acc.center.template': [
        'name', 'acct_book_id', 'acct_org_field_id', 'acct_table_id', 'source_doc_id', 'vou_date_field_id', 
        'voucher_word_id', 'line_ids', 'is_sys_date', 'is_book_vou_word', 'is_combine'
    ]
}


# 参考odoo web_studio: controllers/export.py中xmlid_getter方法
def xmlid_getter():
    """ Return a function that returns the xml_id of a given record. """
    cache = {}

    def get(record, source_doc_model=None):
        """ Return the xml_id of ``record``.
            Raise a ``MissingXMLID`` if ``check`` is true and xml_id is empty.
        """
        if record not in cache:
            # prefetch when possible
            records = record.browse(record._prefetch_ids)
            for rid, val in records.get_external_id().items():
                if val:
                    cache[record.browse(rid)] = val
        if record not in cache and record._name in FIELDS_TO_EXPORT and source_doc_model:
            cache[record] = '__'.join([source_doc_model.replace('.', '_'), record._name.replace('.', '_'), str(record.id)])
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


def get_records_nodes(records, source_doc_model, get_xmlid):
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
        xmlid = get_xmlid(record, source_doc_model)
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
    根据凭证方案记录生成对应结构的数据树
    """
    get_xmlid = xmlid_getter()
    record_nodes = [] # 导出的全部record节点
    for template in templates:
        # 获取凭证方案的配置数据
        lines = template.line_ids
        conditions = lines.condition_id
        summarys = lines.summary_id
        acc_settings = lines.account_setting_id
        acc_setting_lines = acc_settings.line_ids
        acc_conditions = acc_setting_lines.account_condition_id
        acc_auxiliary_settings = acc_setting_lines.auxiliary_set_ids
        source_doc_model = template.source_doc_id.model
        # 按顺序导出，确保加载时不会报错
        for records in (acc_conditions, acc_auxiliary_settings, acc_setting_lines, acc_settings, summarys, conditions, lines, template):
            if records:
                record_nodes.extend(get_records_nodes(records, source_doc_model, get_xmlid))

    return etree.tostring(E.odoo(E.data(noupdate='1', *record_nodes)), encoding="utf-8", pretty_print=True, xml_declaration=True)
    
