/**
    *创建人：王娟
    *当前维护人：王娟
    *Desc：凭证工厂
*/
odoo.define('ps_certificate', function(require, factory) {
    'use strict';
  
    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const datepicker = require('web.datepicker');
    const FactoryMenu = require('web.FactoryMenu');
    const FactoryTable = require('web.FactoryTable');
    const FactoryCard = require('web.FactoryCard');
  
    const _t = core._t;
  
    const CertificateFactory = AbstractAction.extend({
        title: _t('Voucher Factory'),
        contentTemplate: 'CertificateFactory',
  
        events: {
          'click .factory-header-search': '_onSearchData',
          'click .factory-batch-generate': '_onBatchGenerate'
        },
  
        /**
         * @override
         */
        init: function (parent, action, params) {
          action.name = _t('Voucher Factory');
          this._super.apply(this, arguments);
          this.factoryMenu = null; // 菜单
          this.factoryCard = null; // 卡片
          this.factoryTable = null; // 表格
          this.startDate = moment().startOf('month').format('YYYY-MM-DD'); // 开始时间
          this.endDate =  moment().format('YYYY-MM-DD'); // 结束时间
          this.selectedMenuId = null; // 当前选中的菜单
          this.selectedMenuType = 'table'; // 当前选中的菜单类型
          this.tableColumns = [{
              field: 'state',
              checkbox: true,
              align: 'center',
              valign: 'middle',
          },{
              title: _t('Account Book'), // '账簿'
              field: 'accting_book',
              filter: true, 
          },{
              title: _t('Domain'), //'领域', 
              field: 'domain',
              filter: true, 
          },{
              title: _t('Module'), //'模块', 
              field: 'module',
              filter: true, 
          },{
              title: _t('Voucher Sheme'), //'凭证方案', 
              field: 'template',
              filter: true, 
          },{
              title: _t('unPublishNumber'), //'未生成单据数量', 
              field: 'doc_num',
              filter: true, 
          }]
        },
  
        /**
         * @override
         */
        start: function () {
          const self = this;
          const def= [
            self._super.apply(this,arguments),
            self.renderDate(),
            self.renderMenuBar(), 
          ];
          this.$('.factory-card-container').hide();
          return def;
        },
    
        /**
         * 日期
         * @param {*} event 
         */
        renderDate: function () {
            const startDatePiker = this.makeDatePicker(moment().startOf('month'));
            const endDatePiker = this.makeDatePicker();
            startDatePiker.on('datetime_changed', this, function () {
                this.startDate = startDatePiker.getValue().format('YYYY-MM-DD');
                this.rerender(false);
            });
            endDatePiker.on('datetime_changed', this, function () {
                this.endDate = endDatePiker.getValue().format('YYYY-MM-DD');
                this.rerender(false);
            });
            startDatePiker.appendTo(this.$('.factory-header-startDate')).then(function() {});
            endDatePiker.appendTo(this.$('.factory-header-endDate')).then(function() {});
        },
  
        /**
         * 菜单渲染
         * @param {*} event 
         */
        renderMenuBar: function () {
            this.factoryMenu = new FactoryMenu(this, {
                menuTitle: _t('Account Book'), //'账簿',
                requestUrl: '/ps_acc_center/voucher_factory/orgs',
                onSubMenuClick: this.onSubMenuClick.bind(this),
                onLeafMenuClick: this.onLeafMenuClick.bind(this),
            });
            this.factoryMenu.appendTo(this.$('.factory-menu-container'));
        },
  
        /**
         * 列表渲染
         * @param {*} event 
         */
        renderTableBar: function (id) {
          if (id) {this.selectedMenuId = id}
          if (this.factoryTable) {
            this.factoryTable.destroy()
          }
          this.factoryTable = new FactoryTable(this, {
            tableColumns: this.tableColumns,
            requestUrl: '/ps_acc_center/voucher_factory/org/schemes',
            requestParams: {
                org_id: this.selectedMenuId,
                start_date: this.startDate, 
                end_date: this.endDate,
            }
          });
          this.factoryTable.appendTo(this.$('.factory-table-container'));
        },
  
        /**
         * 卡片渲染
         * @param {*} event 
         */
        renderCardBar: function () {
          if (this.factoryCard) {
              this.factoryCard.destroy()
          }
          this.factoryCard = new FactoryCard(this, {
              requestUrl: '/ps_acc_center/voucher_factory/cards',
              requestParams: {
                  accting_book_id: this.selectedMenuId,
                  start_date: this.startDate, 
                  end_date: this.endDate,
              }
          });
          this.factoryCard.appendTo(this.$('.factory-card-container'));
        },
  
        /**
         * 一级菜单点击
         * @param {*} event 
         */
        onSubMenuClick: function(item, cb) {
          this.selectedMenuId = item.menuId;
          this.selectedMenuType = 'table';
          this.rerender()
          cb();
        },
  
        /**
         * 二级菜单点击
         * @param {*} event 
         */
        onLeafMenuClick: function (item, cb) {
          this.selectedMenuType = 'card';
          this.selectedMenuId = item.menuId;
          this.rerender()
          cb();
        },
  
         /**
         * 切换右侧看板
         * @param {*} isRefresh  是否全部刷新
         */
        rerender: function (isRefresh = true) {
          if (this.selectedMenuType === 'table') {
            this.renderTableBar();
            if (isRefresh) {
              this.$('.factory-table-container').show();
              this.$('.factory-card-container').hide();
              this.$('.factory-batch-generate').show();
            }
          } else {
            this.renderCardBar();
            if (isRefresh) {
              this.$('.factory-table-container').hide();
              this.$('.factory-card-container').show();
              this.$('.factory-batch-generate').hide();
            }
          }
        },
        /**
         * 生成日期
         * @param {*} event 
         */
        makeDatePicker: function(defaultDate = moment()) {
          return  new datepicker.DateWidget(this, {
            useCurrent: true, 
            defaultDate: defaultDate
          });
        },
  
        /**
         * 查询
         * @param {*} event 
         */
        _onSearchData: function () {
          const params = {
            startDate: this.startDate,
            endDate: this.endDate
          };
          this.rerender();
        },
  
        /**
         * 批量生成凭证
         * @param {*} event 
         */
        _onBatchGenerate: async function () {
          const selectedData = this.factoryTable.getSelectAllRows();
          if (selectedData.length) {
            let line_ids = [];
            _.map(selectedData, data =>{
              line_ids.push(data.line_id);
            });
            this._rpc({
              route: '/ps_acc_center/voucher_factory/voucher/batch',
              params: {
                data: line_ids, 
                start_date: this.startDate, 
                end_date: this.endDate
              }
            }).then(res => {
              if (res.code === 200 && res.action) {
                this.do_action(
                  res.action, {
                    // todo
                    on_reverse_breadcrumb: function() {},
                  }
                );
              } else  {
                this.displayNotification({
                  type: 'warning',
                  title: _t('friendly tips'),
                  message: _t('fail'),
                  sticky: false
                });
              }
            })
          } else {
            this.displayNotification({
              type: 'warning',
              title: _t('friendly tips'),
              message: _t('Please select operation data'),
              sticky: false
            });
          }
        }
    })
  
    core.action_registry.add('CertificateFactory', CertificateFactory);
    return CertificateFactory
  });