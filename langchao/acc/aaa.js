        /*
         * 渲染单元格的文字信息
         * @param {*} record 
         * @param {*} node 
         * @return {String}
         */
        _renderCellText (record, attrs) {
            const field = this.state.fields[attrs.name];
            let name = attrs.name;
            if (name.includes(this.sublistPrefix)) {
                name = name.replace(this.sublistPrefix + '.', '');
            }
            const value = record.data[name];
            const { precision } = attrs.options ? pyUtils.py_eval(attrs.options) : {};;

            return fieldUtils.format[field.type](value, field, {
                data: record.data,
                escape: true,
                isPassword: 'password' in attrs,
                digits: precision ? [28, utils.getDigits(record, precision[1], precision[0])] : (attrs.digits && JSON.parse(attrs.digits)),
                can_zero: attrs.can_zero  // 判断是否显示0
            });
        },