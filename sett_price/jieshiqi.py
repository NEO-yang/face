# -*- coding: utf-8 -*-
"""
==================================================
@创建人：杨兴财
@当前维护人：杨兴财
@Desc： 结算价目表物料解释器
==================================================
"""

from odoo import _, api, models
from odoo.addons.ps_imp.tools.excel_tools import ExcelTools


COL_INDEX = 1
ROW_INDEX = 2


class ExpOrgImpParse(models.AbstractModel):
    _name = 'mdm.amb.sett.pricelist.line1_ids.material_id'
    _inherit = 'imp.parse.abstract.model'
    _description = 'Amoeba Settlement Price List Material'

    ################################  默认值区 start      ################################

    ################################  默认值区 end       ################################


    ################################  字段定义区 start     ################################

    ################################  字段定义区 end      ################################
    

    ################################  计算方法区 start     ################################

    ################################  计算方法区 end      ################################


    ################################  onchange方法区  start  ################################

    ################################  onchange方法区  end   ################################


    ################################  约束方法区  start    ################################

    ################################  约束方法区  end     ################################


    ################################  服务器动作区  start   ################################

    ################################  服务器动作区  end    ################################


    ################################  按钮动作区  start    ################################

    ################################  按钮动作区  end     ################################


    ################################  私有方法区  start    ################################

    ################################  私有方法区  end     ################################


    ################################  公共方法区  start    ################################

    ################################  公共方法区  end     ################################


    ################################  覆盖基类方法区  start  ################################

    ################################  覆盖基类方法区  end   ################################


    ################################  其他方法区  start    ################################
   
    @api.model
    def parse(self, data, index, name, field, options):
        """
        费用承担组织解释器
        @param data: 单元格数据，二维数组[[‘00’，‘01’，‘02’], []]
        @param index: 当前列的index
        @param name: 列名, 字段名
        @param field: field对象
        @options: 模板
        """
        empty_info = _("The 'Material' cannot be empty")  # 物料不允许为空
        not_exist_info = _('Material does not exist, please re-enter')  # 物料不存在，请重新输入
        # 单元格[%s]原数据为[%s],找到多条对应数据，请修改为更精确的编号或者在更多设置中修改解释器
        multivalued_err = _("The original data of cell [%s] is [%s] and more than one corresponding data is found. Please change it to a more accurate number or modify the interpreter in more settings")
        
        use_org_index = self.p_pre_convert_data_by_column('line1_ids/use_org_id', options, data)
        material_obj = self.env['mdm.material']
        all_material_id = material_obj.search([])
        err_msg_list = []
        for row_index, row in enumerate(data):
            value = row[index]
            use_org_value = row[use_org_index]
            if not value:
                err_msg_list.append({'row_index': row_index, 'err_msg': empty_info})
                row[index] = None
            else:
                target_material_id = all_material_id.filtered_domain(
                    [('use_org_id', '=', use_org_value), 
                    '|', 
                    ('number', '=', value), 
                    ('name', '=', value)]
                    )
                if not target_material_id:
                    err_msg = {
                        'row_index':row_index,
                        'err_msg': not_exist_info
                        }
                    err_msg_list.append(err_msg)
                    row[index] = None
                elif len(target_material_id) > 1:
                    # 多于一个数据
                    coordinate = str(ExcelTools.index2col(index + COL_INDEX)) + str(row_index + ROW_INDEX)
                    err_msg = {
                        'row_index':row_index,
                        'err_msg': multivalued_err % (coordinate, value)
                        }
                    err_msg_list.append(err_msg)
                    row[index] = None
                else:
                    row[index] = target_material_id.id

        return err_msg_list

   ################################  其他方法区  end     ################################