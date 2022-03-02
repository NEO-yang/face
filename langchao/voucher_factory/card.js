/**
*创建人：王娟
*当前维护人：王娟
*Desc：卡片
*/
odoo.define('web.FactoryCard', function(require, factory) {
    'use strict';

    const cardDialog = require('factory.cardDialog');
    const solutionDialog = require('factory.solutionDialog');
    const core = require('web.core');
    const Widget = require('web.Widget');
    const _t = core._t;
    
    const FactoryCard = Widget.extend({
      template: 'FactoryCard',
      events: {
          'click .card-title-remove': '_removeCard',
          'click .card-add-body': '_addCard',
          'click .solution-item-add': '_addSolution',
          'click .solution-item-move': '_removeSolution',
          'click .watch-voucher-btn': '_watchVoucher',
          'click .gen-voucher-btn': '_generateVoucher'
      },

      /**
       * @override
       */
      init: function (parent, params) {
          this._super.apply(this, arguments);
          this.requestUrl = params.requestUrl;
          this.requestParams = params.requestParams;
          this.cardList = []; // 卡片列表
          this.parent = parent;
          $("[data-toggle='tooltip']").tooltip(); 
      },

      /**
       * @override
       */
      willStart: function () {
        let defs = [this._super.apply(this,arguments), this.getCardList()];
        return Promise.all(defs);
      },

      /**
       * @override
       */
      start: function () {
        const defs = [this._super.apply(this, arguments)];
        return Promise.all(defs);
      },

      /**
       * 获取卡片列表
       */
      getCardList: function () {
        return this._rpc({
          route: this.requestUrl,
          params: this.requestParams,
        }).then((res) => {
          if (res.code === 200) {
            this.cardList = res.data;
          } else  {
            this.displayNotification({
              type: 'warning',
              title: _t('friendly tips'),
              message: res.message || _t('fail'),
              sticky: false
            });
          }
        })
      },

      /**
       * 新增卡片
       */
      _addCard: function () {
          const self = this;
          self.cardDialog = new cardDialog(self, {
            requestParams: this.requestParams
          });
          self.cardDialog.open();
      },

      /**
       * 删除卡片
       */
      _removeCard: function (event) {
        this._rpc({
          route: '/ps_acc_center/voucher_factory/card/delete',
          params: {
            accting_book_id: $(event.currentTarget).data('acctingbookid'), 
            module_id: $(event.currentTarget).data('moduleid')
          }
        }).then(res => {
          if (res.code === 200) {
            this.displayNotification({
              type: 'success',
              title: _t('friendly tips'),
              message: _t('successfully'),
              sticky: false
            });
            this.parent.renderCardBar()
          } else {
            this.displayNotification({
              type: 'warning',
              title: _t('friendly tips'),
              message: res.message || _t('fail'),
              sticky: false
            });
          }
        })
      },

      /**
       * 增加方案
       */
      _addSolution: function (event) {
          const self = this;
          self.solutionDialog = new solutionDialog(self, {
            requestParams: {
              accting_book_id: $(event.currentTarget).data('acctingbookid'), 
              module_id: $(event.currentTarget).data('moduleid')
            }
          });
          self.solutionDialog.open();
      },

      /**
       * 删除方案
       */
      _removeSolution: function (event) {
        this._rpc({
          route: '/ps_acc_center/voucher_factory/scheme/delete',
          params: {
            accting_book_id: $(event.currentTarget).data('acctingbookid'), 
            module_id: $(event.currentTarget).data('moduleid'),
            template_id: $(event.currentTarget).data('templateid'),
          }
        }).then(res => {
          if (res.code === 200) {
            this.displayNotification({
              type: 'success',
              title: _t('friendly tips'),
              message: _t('successfully'),
              sticky: false
            });
            this.parent.renderCardBar();
          } else  {
            this.displayNotification({
              type: 'warning',
              title: _t('friendly tips'),
              message: res.message || _t('fail'),
              sticky: false
            });
          }
        })
      },

      /**
       * 查看凭证
       */
      _watchVoucher: function (event) {
        if ($(event.currentTarget).data('vou_num') < 1) {
          this.displayNotification({
            type: 'warning',
            title: _t('friendly tips'),
            message: _t('No voucher to view, please check'), // 暂无可查看凭证, 请检查
            sticky: false
          });
          return;
        }
        this._rpc({
          route: '/ps_acc_center/voucher_factory/vouchers',
          params: {
            start_date: this.requestParams.start_date,
            end_date: this.requestParams.end_date,
            accting_book_id: $(event.currentTarget).data('acctingbookid'),
            template_id: $(event.currentTarget).data('templateid'),
          }
        }).then(res => {
          if (res.code === 200) {
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
              message: res.message || _t('fail'),
              sticky: false
            });
          }
        })
      },

      /**
       * 生成凭证
       */
      _generateVoucher: function (event) {
        this._rpc({
          route: '/ps_acc_center/voucher_factory/voucher/generation',
          params: {
            start_date: this.requestParams.start_date,
            end_date: this.requestParams.end_date,
            line_id: $(event.currentTarget).data('line_id'),
          }
        }).then(res => {
          if (res.code === 200) {
            if (res.action) {
              this.do_action(
                res.action, {
                  // todo
                  on_reverse_breadcrumb: function() {},
                }
              );
            } else {
              this.displayNotification({
                type: 'success',
                title: _t('friendly tips'),
                message: _t('Coming soon'),
                sticky: false
              });
            }
          } else  {
            this.displayNotification({
              type: 'warning',
              title: _t('friendly tips'),
              message: res.message || _t('fail'),
              sticky: false
            });
          }
        })
      },
    })

    return FactoryCard;
});