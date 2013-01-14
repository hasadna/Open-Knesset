!function ($) {

"use strict"; // jshint ;_;

	var OKMore = function (element, options, source) {
		this.$element = $(element)
		this.$source = $(source)
		this.options = $.extend({}, $.fn.okmore.defaults, options)

		this.initial = parseInt(this.options.initial);
		this.page = parseInt(this.options.page);
		this.total = parseInt(this.options.total);
		this.callback = this.options.callback ? window[this.options.callback] : null;
	}

	OKMore.prototype = {
		constructor: OKMore

		, getMore: function() {
        var that = this;

        this.$source.button('loading');
        
        $.ajax({
          url: this.options.url,
          data:{initial: this.initial, page:this.page+1},
          context:this
        }).done(function(data) {
          $(data.content).appendTo(this.$element);
          this.page = data.current;
          this.total = data.total;
          this.initial = null;

          if (data.has_next) {
            this.$source.button('reset');
          }
          else {this.$source.remove()}

		  if (this.callback) this.callback();
        });

		}
	}

  var old = $.fn.okmore

  $.fn.okmore = function (source) {
    var $source = $(source)
      , source_options = $source.data();

    source_options.url = source_options.url || $source.attr("href");

    return this.each(function () {
      var $this = $(this)
        , data = $this.data('okmore')
        , options = source_options;

      if (!data) $this.data('okmore', (data = new OKMore(this, options, source)))

      data.getMore()
    })
  }

  $.fn.okmore.defaults = {
    page: 0,
    initial: 2,
    total: 999999,
	callback: null
  }

  $.fn.okmore.Constructor = OKMore


 /* okmore NO CONFLICT
  * ==================== */

  $.fn.okmore.noConflict = function () {
    $.fn.okmore = old
    return this
  }


 /* okmore DATA-API
  * ================= */
  $(document).on('click.okmore.data-api', '[data-provide=okmore]', function (e) {
      
      var $this = $(this)
        , target = $this.attr('data-target');
      e.preventDefault();
      $(target).okmore(this)
  })
}(window.jQuery);
