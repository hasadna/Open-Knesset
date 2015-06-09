!function ($) {

  "use strict"; // jshint ;_;

  // reset function for forms
  jQuery.fn.reset = function () {
    $(this).each (function() { this.reset(); });
  }

	
	$('.btn-inc').click(modifyZoomBy.bind(undefined,0.3));
	$('.btn-dec').click(modifyZoomBy.bind(undefined,-0.3));

	function modifyZoomBy(multiplier) {
		document.body.style.zoom = parseFloat(document.body.style.zoom || 100) * (1+ multiplier) + "%";
	}
  /***************************************************************
   * handle submission event of suggestion forms
   ***************************************************************/
  function suggestionFormSubmit() {

	var $modal = $(this).closest('.suggest-modal'),
		$btn = $('.btn-primary', $modal),
		$this = $(this);

		// don't send if already sending
		if ($btn.attr('disabled') === 'disabled') {
			return false;
		}

		// Remove pre-existing errors
		$('.text-error', $this).remove();
		$btn.button('loading');

		$.post($this.attr('action'), $this.serialize())
		.done(function(data){
			if (data.success) {
			var container = $('<div class="alert"><a href="#" class="close" data-dismiss="alert">&times;</a></div>'),
			msg = $('<span/>').text(gettext("Your suggestion is submitted. Thank you !"));

			msg.appendTo(container);

			$($('.container').get(1)).prepend(container);
			container.alert();

			$this.reset();
			$modal.modal('hide');
			}
			else {
				// we assume we got the validation errors in data.errors object
				// TODO handle form validation errors for __all__

				$.each(data.errors, function(key, item_errors) {
					var el = $('<div class="text-error"/>'),
						target = $('[name=' + key  +']', $this);

					el.insertAfter(target).text(item_errors.join());

				})
			}
		})
		.fail(function(data) {
			var container = $('<div class="alert alert-error"><a href="#" class="close" data-dismiss="alert">&times;</a></div>'),
			msg = $('<span/>').text(data.responseText.substring(0, 100));

			msg.appendTo(container);

			$this.prepend(container);
		})
		.always(function() {
			$btn.button('reset');
		})
		return false;
	}

  /***************************************************************
   *  return the params to query for pending suggestions, 
   *  based on suggestion forms we have.
   ***************************************************************/
  function getPendingParams() {
	var getCountFor = $('.suggest-modal form').map(function() {
		var $el = $(this),
			res = $el.data('forModel'),
			pk = $el.data('forPk');
		
		if (pk) {
			res = res + '-' + pk;
		}
		return {name: 'for', value:res};
	}).get();

	return getCountFor;
  }


  /***************************************************************
   * Shows the pending counts in a newly created alert. 
   * Creates a button for showing the details and returns it
   ***************************************************************/
  function showPendingCounts(data) {
	// remove old alerts if exists
	$('.alert-pending-suggestions-count').remove();

	var container = $(
			'<div class="alert alert-info alert-pending-suggestions-count">' +
			'<a href="#" class="close" data-dismiss="alert">&times;</a>' +
			gettext('Pending suggestions') +
			':<ul/></div>'),
		suggestion_ul = $('ul', container),
		detail = $('<a href="#" class="btn btn-info"></a>')
				 .text(gettext('View pending suggestions'));

	detail.insertAfter(suggestion_ul);

	$.each(data, function(key, val){
		var suggestion_li = $('<li/>');
		suggestion_li.text(key+ ': ' + val);
		suggestion_li.appendTo(suggestion_ul);
	})

	$($('.container').get(1)).prepend(container);
	container.alert();

	return detail;
  }

  /***************************************************************
   * Creates the suggestion details li for the label, nests a ul
   * with li's for each suggestion type details
   ***************************************************************/
  function createSuggestionDetail(label, suggestions) {
	var label_li = $('<li/>').text(suggestions.length + ' ' + label),
		suggestions_ul = $('<ul/>');

	$.each(suggestions, function(idx, suggest) {
		var s_li = $('<li/>').text(': ' + suggest.label),
			s_actions = $('<div class="suggestion-actions"/>').appendTo(s_li);

		$('<span/>').text(suggest.suggested_at)
		.prependTo(s_li);

		$('<a/>').attr({target:'_blank', href:suggest.by_url})
		.text(suggest.by)
		.prependTo(s_li);

		if (suggest.by_email) {

			// TODO make this an option
			var TITLE_SEPARATOR = '|',
				parts = document.title.split(TITLE_SEPARATOR),
				title = $.trim(parts[parts.length -1]),
				msg_subject = '[' + title + '] ' + gettext('Your Feedback message'),
				msg_body_pre = gettext('Hello %s\n\n%s'),
				msg_body = interpolate(msg_body_pre, [suggest.by, suggest.label.substring(0,150)]); // we must shorten the content, otherwise long urls will trigger an error

			$('<a>').attr({
				href: 'mailto:' + suggest.by_email + '?subject=' + encodeURIComponent(msg_subject) + '&body=' + encodeURIComponent(msg_body),
				class: "btn btn-mini btn-info",
				target: "_blank"
			})
			.text(gettext('Send email'))
			.appendTo(s_actions);
		}

		if (suggest.apply_url) {
			$('<a>')
			.attr({href:suggest.apply_url, class:"btn btn-mini btn-success"})
			.text(gettext('Apply'))
			.appendTo(s_actions)
			.click(handleApplyReject);
		}

		if (suggest.reject_url) {
			$('<a>')
			.attr({href:suggest.reject_url, class:"btn btn-mini btn-warning"})
			.text(gettext('Reject'))
			.appendTo(s_actions)
			.click(handleApplyReject);
		}

		suggestions_ul.append(s_li);
	})

	label_li.append(suggestions_ul);

	return label_li;
  }

  
  /***************************************************************
   * Handle suggestion apply/reject buttons.
   ***************************************************************/
  function handleApplyReject(ev) {
	var btn = $(this),
		url = btn.attr('href'),
		reject = btn.hasClass('btn-warning'),
		data = {};

	if (reject) {
		var reason = prompt(gettext("Reject reason"));

		if (reason == null || reason == "") {return};
		data['reason'] = reason
	}

	$.post(url, data)
	.then(function(res) {
		if (!res.success) {
			alert(res.message || 'Unknown error')
		}
		btn.closest('li').fadeOut(1000, function() { $(this).remove() });
	});

	return false;
  }

  $(function() {
	  // setup submit button
	  $('.suggest-modal .btn-primary').click(function() {
		  var $form = $('form', $(this).closest('.suggest-modal'));
		  $form.submit();
	  });

	  // setup form submmission
	  $('.suggest-modal form').submit(suggestionFormSubmit)

	var getCountFor = getPendingParams();

	if (getCountFor.length > 0) {
		var countUrl = $('.suggest-modal form').data('countUrl'),
			detailUrl =  $('.suggest-modal form').data('detailUrl');

		// Get the pending suggestions for each suggestion form
		$.get(countUrl, getCountFor)
		.done(function(data) {
			if ($.isEmptyObject(data)) { return; }

			var detail = showPendingCounts(data);

			detail.click(function(ev) {
				ev.preventDefault();

				var modal = $('#suggest-viewDetails-modal'),
					target  = modal.find('.modal-body ul').empty();

				$.get(detailUrl, getCountFor)
				.done(function(data) {
					$.each(data, function(label, suggestions) {
						target.append(createSuggestionDetail(label, suggestions));
					})
				})
				.fail(function() {
					target.append(
						$('<li>').text(gettext('You have to be logged in to view suggestions.')));
				})
				.always(function() {
					modal.modal();
				});
				return false;
			});
		})
		// end getting pending suggestions
	}
  }) // end ready
}(window.jQuery);
