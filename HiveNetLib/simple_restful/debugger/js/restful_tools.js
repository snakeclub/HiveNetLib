/**
 * Copyright 2018 黎慧剑
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */

/**
 * simple_restful 模块配套的Web前端工具JS代码
 * @file (restful_tools.js)
 * @author (黎慧剑)
 * @version (0.1.0)
 * @requires jquery-3.5.1.min.js
 * @requires jsencrypt.min.js
 */

;
(function ($) {

    /**
     * simple_restful 模块配套的Web前端工具
     * @class restful_tools
     */
    $.restful_tools = new Object();


    /**
     * 在告警框提示debug信息($.debug为true的情况下才执行)
     * @param {string} str - 要提示的信息
     */
    function debug(str) {
        if ($.debug === true) {
            alert('debug: ' + str);
        }
    };

    /** ---------------------------
     * 字符串编码
     */

    /**
     * 将字符串转换为UTF-8的编码字节
     * @param {string} text - 要编码的字符串
     * @returns {array} - 编码后的字节数组
     */
    $.restful_tools.encode_utf8 = function(text){
        const code = encodeURIComponent(text);
        const bytes = [];
        for (var i = 0; i < code.length; i++) {
            const c = code.charAt(i);
            if (c === '%') {
                const hex = code.charAt(i + 1) + code.charAt(i + 2);
                const hexVal = parseInt(hex, 16);
                bytes.push(hexVal);
                i += 2;
            } else bytes.push(c.charCodeAt(0));
        }
        return bytes;
    };

    /**
     * 将UTF-8的编码字节转换为字符串
     * @param {array} bytes - UTF-8编码的字节数组
     * @returns {array} - 解码后的字符串
     */
    $.restful_tools.decode_utf8 = function(bytes){
        var encoded = "";
        for (var i = 0; i < bytes.length; i++) {
            encoded += '%' + bytes[i].toString(16);
        }
        return decodeURIComponent(encoded);
    };


    /** ---------------------------
     * RSA 加解密相关
     */
    $.restful_tools.rsa_encrypt_obj = new JSEncrypt();  // rsa 加密对象

    /**
     * 设置加密对象的公钥
     * @param {string} public_key_str - 加密公钥字符串
     */
    $.restful_tools.set_rsa_public_key = function(public_key_str){
        $.restful_tools.rsa_encrypt_obj.setPublicKey(public_key_str);
    };

    /**
     * 进行字符串加密处理
     * @param {string} input_str - 要加密的字符串
     */
    $.restful_tools.rsa_encrypt = function(input_str){
        return $.restful_tools.rsa_encrypt_obj.encrypt(input_str);
    };


})(jQuery);