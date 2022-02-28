      schemes = request.env['acc.center.template'].search([])
      books = request.env.ref('ps_mdm.mdm_account_book_data_01')
      for scheme in schemes:
         modules_id = request.env['acc.center.voucher.generation'].search([])
         if not modules_id or scheme.source_module_id not in modules_id.module_id:
            request.env['acc.center.voucher.generation'].create({
               'acct_book_id': books.id,
               'module_id': scheme.source_module_id.id,
               'line_ids':[{
                  # 'parent_id': card_id.id,
                  'source_doc_id': scheme.source_doc_id.id,
                  'source_doc_model': scheme.source_doc_id.model,
                  'template_id': scheme.id}]
                  
               })