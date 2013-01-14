/* =============================================================
 * Open Knesset toggle plus minus
 * Based on bootstrap oktoggle
 * =============================================================
 * Copyright 2012 Twitter, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * ============================================================ */


!function ($) {

  "use strict"; // jshint ;_;


  var OKToggle = function (element, options, source) {
    this.$element = $(element)
	this.$source = $(source)
    this.options = $.extend({}, $.fn.oktoggle.defaults, options)

    this.options.toggle && this.toggle()
  }

  OKToggle.prototype = {

    constructor: OKToggle

  , show: function () {
	  var that = this;
	  this.$element.show('fast', function() {
		  that.$element.addClass('in');
		  that.setSourceText();
	  })
    }

  , hide: function () {
	  var that = this;
	  this.$element.hide('fast', function() {
		  that.$element.removeClass('in');
		  that.setSourceText();
	  })
    }

  , toggle: function () {
      this[this.$element.hasClass('in') ? 'hide' : 'show']()
    }

  , setSourceText: function() {
	  var that = this,
		  idx = this.$element.hasClass('in') ? 1 : 0;
	  this.$source.each(function() {
		$(this).text(that.options.text.split('|')[idx])
	  })
    }

  }


 /* oktoggle PLUGIN DEFINITION
  * ========================== */

  var old = $.fn.oktoggle

  $.fn.oktoggle = function (option, source) {
    return this.each(function () {
      var $this = $(this)
        , data = $this.data('oktoggle')
        , options = typeof option == 'object' && option
      if (!data) $this.data('oktoggle', (data = new OKToggle(this, options, source)))
      if (typeof option == 'string') data[option]()
    })
  }

  $.fn.oktoggle.defaults = {
    toggle: true,
	text: 'Show +|Hide -'
  }

  $.fn.oktoggle.Constructor = OKToggle


 /* oktoggle NO CONFLICT
  * ==================== */

  $.fn.oktoggle.noConflict = function () {
    $.fn.oktoggle = old
    return this
  }


 /* oktoggle DATA-API
  * ================= */

  $(document).on('click.oktoggle.data-api', '[data-toggle=oktoggle]', function (e) {
    e.preventDefault();
    var $this = $(this), href
      , target = $this.attr('data-target')
        || e.preventDefault()
        || (href = $this.attr('href')) && href.replace(/.*(?=#[^\s]+$)/, '') //strip for ie7
      , option = $(target).data('oktoggle') ? 'toggle' : $this.data()
    $this[$(target).hasClass('in') ? 'addClass' : 'removeClass']('oktoggled')
    $(target).oktoggle(option, this)
  })

}(window.jQuery);
