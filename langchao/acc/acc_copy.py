@sys_ele_ctrl()
    def svc_run_copy(self):
        """
        凭证方案复制函数
        """
        for rec in self:
            lines = []
            for line in rec.line_ids:  # 凭证方案明细表
                account_setting_id = line.account_setting_id  # 科目设置字段
                account_setting_line_data = []
                for setting_line in account_setting_id.line_ids:  # 科目设置明细表
                    auxiliary_set_list = []
                    for auxiliary_set_id in setting_line.auxiliary_set_ids:    # 核算维度表
                        new_auxiliary_set_id = auxiliary_set_id.copy()   # 新的核算维度数据
                        auxiliary_set_list.append((4, new_auxiliary_set_id.id))
                    setting_line_data = {'auxiliary_set_ids': auxiliary_set_list}
                    new_setting_line = setting_line.copy(default=setting_line_data)  #新的科目设置明细行数据
                    account_setting_line_data.append((4, new_setting_line.id))
                account_setting_data ={'line_ids': account_setting_line_data}
                new_account_setting_id = line.account_setting_id.copy(default=account_setting_data)   #新的科目设置数据
                template_line_data = {'account_setting_id': new_account_setting_id.id}
                line_rec = line.copy(default=account_setting_line_data)
                lines.append((4, line_rec.id))  
            vals = {}
            vals['line_ids'] = lines
            records_num = self.search_count([('name', 'like', rec.name),('delete_state', '=', 'normal')])
            vals['name'] = rec.name + '(' + str(records_num) + ')'  #原name+(累加数字)
            rec.copy(default=vals)




<?xml version="1.0" encoding="UTF-8" ?>
<!-- 
==================================================
@创建人 王琨鹏
@当前维护人 ：Vic Sun
@Desc ：凭证方案
==================================================
-->
<odoo>
    <data>
        <!--tree-->
        <record id="acc_center_template_tree_view" model="ir.ui.view">
            <field name="name">acc.center.template.tree.view</field>
            <field name="model">acc.center.template</field>
            <field name="arch" type="xml">
                <tree string="Voucher Scheme" isAdvancedBtn="true" hasDefaultBtn="false">
                    <buttonspack>
                        <button string="Create" special="create" type="event" isBatch="false"/>
                        <button string="Delete" type="object" isBatch="true" name="svc_run_delete" condition="readonly"/>
                        <button string="Forbid" type="object" isBatch="true" name="svc_run_forbid" condition="readonly"/>
                        <button string="Enable" type="object" isBatch="true" name="svc_run_enable" condition="readonly"/>
                        <button string="Copy" type="object" isBatch="false" name="svc_run_copy" condition="readonly"/>
                        <button string="Generate Voucher Scheme File" type="object" isBatch="true" name="svc_generate_template_file" condition="readonly"/>
                    </buttonspack>
                    <field name="source_doc_id"/>
                    <field name="name" widget="link"/>
                    <field name="acct_table_id"/>
                    <field name="forbid_state"/>
                </tree>
            </field>
        </record>

        <record id="acc_center_template_tree_search" model="ir.ui.view">
            <field name="name">acc.center.template.tree.view.search</field>
            <field name="model">acc.center.template</field>
            <field name="arch" type="xml">
                <search string="Voucher Scheme Search">
                    <field name="name"/>
                    <treewidget treeId="acc_center_search_tree" treeType="search" option='{"isAll": "true"}'>
                        <treenode name="name" model="ps.ir.domain" domain="[('node_id', '=', 'source_domain_id')]">
                            <treenode name="summary" model="ir.module.module" domain="[('node_id','=','source_module_id')]" 
                                relation="ps_domain_id" params="[('state','=','installed'), ('application','=',True)]">
                                <!-- todo: 没有白名单之前，特殊处理资产卡片过滤显示表体 -->
                                <treenode name="name" model="ir.model" relation="ps_module_id" domain="[('node_id', '=', 'source_doc_id')]"
                                    params="[('ps_is_access_control','=',True),'|', '&amp;', ('model_type', '=', 'document'), ('model', '!=', 'fa.asset.card'), ('model', '=', 'fa.asset.card.line1.policy')]" 
                                    attrs="{'can_bring': '1', 'bring_name':'source_doc_id'}"/>
                            </treenode>
                        </treenode>
                    </treewidget>
                </search>
            </field>
        </record>

        <record id="acc_center_template_form_view" model="ir.ui.view">
            <field name="name">acc.center.template.form.view</field>
            <field name="model">acc.center.template</field>
            <field name="arch" type="xml">
                <form string="Voucher Scheme" isAdvancedBtn="true" hasDefaultBtn="false">
                    <buttonspack>
                        <button string="Edit" special="edit" type="event" isBatch="false"/>
                        <button string="Create" special="create" type="event" isBatch="false"/>
                        <button string="Save" special="save" type="event" isBatch="false"/>
                        <button string="Cancel" special="cancel" type="event" isBatch="false"/>
                        <button string="Delete" type="object" isBatch="false" name="svc_run_delete" condition="readonly"/>
                        <button string="Copy" type="object" isBatch="false" name="svc_run_copy" condition="readonly"/>
                        <button string="Forbid" type="object" isBatch="false" name="svc_run_forbid" condition="readonly" 
                            attrs="{'invisible': [('forbid_state', '!=', 'normal')]}"/>
                        <button string="Enable" type="object" isBatch="false" name="svc_run_enable" condition="readonly" 
                            attrs="{'invisible': [('forbid_state', '!=', 'forbid')]}"/>
                        <button string="Generate Voucher Scheme File" type="object" isBatch="false" name="svc_generate_template_file" condition="readonly"/>
                    </buttonspack>
                    <header>
                        <field name="forbid_state" widget="statusbar" copy="0"/>
                    </header>
                    <sheet>
                        <group col="8">
                            <field colspan="2" name="number" readonly="1"/>
                            <field colspan="2" name="name" required="1" attrs="{'readonly': [('forbid_state', '=', 'normal')]}"/>
                            <field colspan="2" name="source_doc_id" options="{'no_create': True, 'no_open': True}" required="1" warning_dialog="1"
                                attrs="{'readonly': [('forbid_state', '=', 'normal')]}" 
                                domain="['|', '&amp;', ('model_type', '=', 'document'), ('model', 'not in', ['fa.asset.card', 'gl.memorandum']), ('model', 'in', ['fa.asset.card.line1.policy', 'gl.memorandum.line2'])]"/>
                            <field colspan="2" name="acct_org_field_id" attrs="{'readonly': [('forbid_state', '=', 'normal')]}" 
                                domain="[('model_id', '=', source_doc_id), ('relation', '=', 'sys.admin.orgs'), ('ttype', '=', 'many2one')]" 
                                options="{'no_create': True, 'no_open': True}" required="1"/>
                            
                            <field colspan="2" name="acct_table_id" options="{'no_create': True, 'no_open': True}" required="1" warning_dialog="1" 
                                attrs="{'readonly': [('forbid_state', '=', 'normal')]}"/>
                            <field colspan="2" name="is_sys_date" attrs="{'readonly': [('forbid_state', '=', 'normal')]}"/>
                            <field colspan="2" name="vou_date_field_id" 
                                attrs="{'readonly': [('forbid_state', '=', 'normal')]}" required="1" 
                                domain="[('model_id', '=', source_doc_id), ('ttype', 'in', ['date', 'datetime'])]" 
                                options="{'no_create': True, 'no_open': True}"/>        
                            <field colspan="2" name="is_combine" attrs="{'readonly': [('forbid_state', '=', 'normal')]}"/>

                            <field colspan="2" name="is_fetch_other_model" attrs="{'readonly': [('forbid_state', '=', 'normal')]}"/>
                            <!-- 注意：凭证取数需要取非主表及表体数据时，需要勾选参数【其他模型取数】，配置第三方模型与取数模型关联关系后可参与取数。 -->
                            <div colspan="6">
                                Note: When the voucher extract needs to take non-main table and table body data, you need to check the parameter "Other model fetches" and participate in the extract after configuring the relationship between the third-party model and the extract model.
                            </div>

                            <field colspan="2" name="is_formula"/>

                            <field name="source_doc_model" invisible="1"/>
                        </group>
                        <notebook>
                            <page string="Voucher Scheme Line">
                                <field name="line_ids" widget="one2many" attrs="{'readonly': [('forbid_state', '=', 'normal')]}" mode="virtuallist">
                                    <virtuallist isAdvancedBtn="true" hasDefaultBtn="false" editable="bottom" rownumber="6">
                                        <buttonspack>
                                            <button string="Insert Line" isBatch="true" condition="readonly" special="insertLine" type="event"/>
                                            <button string="Copy Line" isBatch="true" condition="readonly" special="copyLine" type="event"/>
                                        </buttonspack>
                                        <field name="sequence" attrs="{'column_invisible': 1}"/>
                                        <field name="fetch_id" options="{'no_create': False}" 
                                            attrs="{
                                                'column_invisible': [('parent.is_fetch_other_model', '=', False)], 
                                                'required': [('parent.is_fetch_other_model', '=', True)]}"
                                            domain="[('model_id', '=', parent.source_doc_id), ('model_id', '!=', False)]" 
                                            context="{'default_model_id': parent.source_doc_id}"/>
                                        <field name="condition_id" options="{'no_create': False}" 
                                            domain="[('model_id', '=', parent.source_doc_id), ('model_id', '!=', False)]" 
                                            context="{'default_model_id': parent.source_doc_id}"/>
                                        <field name="summary_id" options="{'no_create': False}" required="1" 
                                            domain="[('source_doc_id', '=', parent.source_doc_id), ('source_doc_id', '!=', False)]" 
                                            context="{'default_source_doc_id': parent.source_doc_id}"/>
                                        <field name="account_setting_id" options="{'no_create': False}" required="1" 
                                            domain="[('id', '=', account_setting_id), ('delete_state', '=', 'normal')]"
                                            context="{
                                                'default_acct_table_id': parent.acct_table_id, 
                                                'default_source_doc_id': parent.source_doc_id,
                                                'default_model_domains': model_domains}"/>
                                        <field name="direction" required="1"/>
                                        <field name="curr_field_id" options="{'no_create': True, 'no_open': True}" required="1" 
                                            domain="[('model_id', '=', model_domains), ('relation', '=', 'mdm.currency'), ('ttype', '=', 'many2one')]" />
                                        <field name="curr_rate_field_id" options="{'no_create': True, 'no_open': True}" 
                                            domain="[('model_id', '=', model_domains), ('name', 'ilike', 'rate'), ('ttype', '=', 'float')]"/>

                                        <!-- 不配置公式，直接选择字段 -->
                                        <field name="amount_field_id" options="{'no_create': True, 'no_open': True}" 
                                            domain="[('model_id', 'in', model_domains), ('ttype', '=', 'float')]" 
                                            attrs="{'column_invisible': [('parent.is_formula', '=', True)], 'required': [('parent.is_formula', '=', False)]}"/>
                                        <field name="standard_amount_field_id" options="{'no_create': True, 'no_open': True}"
                                            domain="[('model_id', 'in', model_domains), ('ttype', '=', 'float')]"
                                            attrs="{'column_invisible': [('parent.is_formula', '=', True)], 'required': [('parent.is_formula', '=', False)]}"/>
                                        <field name="model_domains" invisible="1"/>
                                        <!-- 配置计算公式 -->
                                        <field name="amount_model_id" options="{'no_create': True, 'no_open': True}" domain="[('id', 'in', model_domains)]"
                                            attrs="{'column_invisible': [('parent.is_formula', '=', False)], 'required': [('parent.is_formula', '=', True)]}"/>
                                        <field name="amount_formula" formula_field_depends="amount_model_id" widget="formula_field"
                                            attrs="{'column_invisible': [('parent.is_formula', '=', False)], 'required': [('parent.is_formula', '=', True)]}"/>
                                        <field name="amount_local_formula" formula_field_depends="amount_model_id" widget="formula_field"
                                            attrs="{'column_invisible': [('parent.is_formula', '=', False)], 'required': [('parent.is_formula', '=', True)]}"/>

                                    </virtuallist>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>
            </field>
        </record>

        <record model="ir.actions.act_window" id="action_acc_center_template">
            <field name="name">Voucher Scheme</field>
            <field name="res_model">acc.center.template</field>
            <field name="view_mode">tree,form</field>
            <field name="domain">[('delete_state', '=', 'normal')]</field>
        </record>
        <menuitem
            id="menu_acc_center_template"
            name="Voucher Scheme"
            web_icon="ps_acc_center,static/description/icon.png"
            action="action_acc_center_template" 
            parent="menu_daily_process"
            sequence="10"/>
    </data>
</odoo>