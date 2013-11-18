function hide_annotation_form(annoid) {
    $("#annotationform-"+annoid).hide();
    $("#annotations-"+annoid).show();
    $("#selectable-"+annoid).text(gettext("Annotate"));
    $("#annotationrealform-"+annoid)[0].reset();
    $("#editable-"+annoid).show();
    if(annotation_objects[annoid].annotation_count >0){
      $("#annotationtoolbox-"+annoid).show();
    }
}
$(function(){
    var options_bill = { 
         serviceUrl:'/bill/auto_complete/',
         minChars:2, 
         maxHeight:400,
         width:400,
         deferRequestBy: 100, //miliseconds
         onSelect: function(value, data, me){ 
            me.siblings("input[name$='bill_id']").val(data);
            me.siblings("input[type$='submit']").removeAttr('disabled'); },
         };

    var options_mk = { 
         serviceUrl:'/member/auto_complete/',
         minChars:0, 
         maxHeight:400,
         width:150,
         deferRequestBy: 100, //miliseconds
         };

    $('input.bill_input').autocomplete(options_bill);
    $('input.bill_input').keydown(function() { 
        $(this).siblings("input[name$='bill_id']").val('');
        $(this).siblings("input[type$='submit']").attr('disabled', 'disabled'); });
    $("input[name$='mk_name']").autocomplete(options_mk);

    $(".annotation-content").each(function(){
        var annoid = $(this).attr("id").split("-")[1];
        annotation_objects[annoid] = new Annotations(annoid);
    });
    for(var a in annotation_objects){
        annotation_objects[a].importQuotes();
        annotation_objects[a].insertQuotes();
    }
    $(".annotationform-link").click(function(e){
      e.preventDefault();
      if (!window.logged_in) {
          var msg = gettext("Sorry, only logged users can annotate.");
          $.jGrowl(msg, {sticky: true});
          return false
      }
      if (!window.permission) {
          var msg = $("#message_permission").html()
          $.jGrowl(msg, {sticky: true});
          return false
      }

      var annoid = $(this).attr("id").split("-")[1];
      annotation_objects[annoid].toggleSelectView();
      if($("#annotations-"+annoid).css("display")=="none"){
        hide_annotation_form(annoid);
      } else{
        if (!$("#annotationform-"+annoid).length) {
            var speech_part = {id: annoid, length: window.parts_lengths[annoid] };
            $("#annotations-"+annoid).before(tmpl("annotationform", {speech_part: speech_part}))
            $(".annotationform-cancel").click(function(e) {
                e.preventDefault();
                var annoid = $(this).attr("id").split("-")[1];
                annotation_objects[annoid].toggleSelectView();
                hide_annotation_form(annoid);
            });
          $("#annotationrealform-"+annoid).submit(function(e){
            var id = $(this).attr("id").split("-")[1];
            if($("#selection_start-"+id).val()=="" || $("#selection_end-"+id).val()==""){
              alert(gettext("Please make a selection."));
              e.preventDefault();
              return false;
            }
            return true;
          });
            $('input[name=color]').colorPicker();
        }
        else
            $("#annotationform-"+annoid).show();
        $(this).text(gettext("Cancel"));
        $("#annotations-"+annoid).hide();
        $("#editable-"+annoid).hide();
        $("#annotationtoolbox-"+annoid).hide();
      }
    });
  $(".markall").click(function(e){
    var aid = $(this).attr("id").split("-")[1];
    if($(this).attr('checked')){
      annotation_objects[aid].updateDefaultAnnotationColor("self");
    } else{
      annotation_objects[aid].updateDefaultAnnotationColor("inherit");
    }
  });
  $(".reallydelete").live("submit", function(e){
    var anno_id = $(this).children('[name=annotation_id]').val();
    var username = $('#annotation-'+anno_id+' a.user-link').html();

    if (!window.is_staff && username != window.username){
        var msg = $("#message_staff").html()
        $.jGrowl(msg, {sticky: true});
        return false
    }
    return confirm(gettext('Delete can not be un-done. Are you sure?'));
  });
  $(".annotationflagselect").change(function(e){
    var id = $(this).parents("form").attr("id").split("-")[1];
    var val = parseInt($(this).val());
    var color = null;
    switch(val){
      case 0: // Put more colors here
        color = "#99ccff"; break;
    }
    if(color != null){
      $("#color_value").val(color);
      $("#annotationcolor-"+id).val(color);
      $("div.color_picker").css("background-color", color); 
    }
  });
  $(".toggle").live("click", function(e){
     e.preventDefault();
     var id = $(this).attr("id");
     if (id == ""){
       var url = $(this).attr("href");
       var sel = $("."+url.substring(1,url.length)+"-container");
     } else {var sel = $("#"+id+"-container");}
     sel.toggle();
  });

    /** infinite scroll **/

    (function(){
        var _isFloat = false;
        var _isFooterVisible = false;

        var _isActive = function() {
            return ($(window).width() > 1200 && $(window).height() > 500);
        };

        var _float = function() {
            var appheader = $('#app-header');
            var body = $('body');
            var breadcrumb = $('section.container > ul.breadcrumb');
            var sidebar = $('#content-main > div > div.row > div.span3');
            var appheader_margin_left = appheader.css('margin-left');
            var appheader_margin_right = appheader.css('margin-right');
            var sidebar_left = sidebar.position().left;
            var breadcrumbheight = breadcrumb.height();
            body.addClass('infinity-protocol');
            appheader.css({
                'padding-left' : appheader_margin_left,
                'padding-right' : appheader_margin_right,
                'background' : body.css('background')
            });
            var appheader_height = appheader.height();
            var headerHeight = breadcrumbheight + appheader_height + 25;
            breadcrumb.css({
                'top' : appheader_height + 'px',
                'background' : body.css('background'),
            });
            sidebar.css({
                'top' : headerHeight+'px',
                'left' : sidebar_left + 'px',
                'height' : ($.waypoints('viewportHeight') - headerHeight - 5) + 'px',
            });
        };

        var _unfloat = function() {
            $('body').removeClass('infinity-protocol');
            $('#content-main > div > div.row > div.span3').removeAttr('style');
            $('#app-header').removeAttr('style');
            $('section.container > ul.breadcrumb').removeAttr('style');
        };

        var _showFooterInfinityLoader = function(){
            $('#protocolinfiniloader').removeClass('hidden');
        };

        var _hideFooterInfinityLoader = function(){
            $('#protocolinfiniloader').addClass('hidden');
        };

        var _curPage = null;
        var _baseUrl = null;
        var _getNextPageUrl = function() {
            if (_curPage == null) {
                var re = /page=([0-9]*)/;
                var matches = window.location.href.match(re);
                if (matches != null && matches.length == 2) {
                    _curPage = parseInt(matches[1]);
                    _baseUrl = window.location.href.replace(re, 'page=((PAGE))');
                } else {
                    _curPage = 1;
                    if (window.location.href.indexOf('?')>-1) {
                        _baseUrl = window.location.href + '&page=((PAGE))';
                    } else {
                        _baseUrl = window.location.href + '?page=((PAGE))';
                    };
                };
            };
            _curPage++;
            return _baseUrl.replace('((PAGE))', _curPage);
        };

        var _isFooterAbove = function() {
            var ans = false;
            $.each($.waypoints('above'), function(i, elt) {
                if (elt.id == 'app-footer') {
                    ans = true;
                }
            });
            return ans;
        }

        var _onProtocolWaypoint = function(direction) {
            if (!_isFooterVisible && _isActive()) {
                if (direction == 'down') {
                    _isFloat = true;
                    _float();
                } else if (direction == 'up') {
                    _isFloat = false;
                    _unfloat();
                };
            };
        };

        var _noMorePages = false;
        var _isLoadingNextPage = false;
        var _onFooterWaypoint = function(direction) {
            if (direction == 'down') {
                _isFooterVisible = true;
                _unfloat();
                if (!_noMorePages && !_isLoadingNextPage) {
                    var _nextPage = _getNextPageUrl();
                    _showFooterInfinityLoader();
                    _isLoadingNextPage = true;
                    $("<div>").load(_nextPage+' #committeeprotocol', function(){
                        var html=$(this).find('.protocol').html();
                        html = $.trim(html);
                        $('#committeeprotocol').append(html);
                        if (html.length == 0) {
                            _noMorePages = true;
                        };
                        _hideFooterInfinityLoader();
                        _setFooterWaypoint();
                        if (!_isFooterAbove()) {
                            _onFooterWaypoint('up');
                        }
                        _isLoadingNextPage = false;
                    });
                };
            } else {
                _isFooterVisible = false;
                if (_isFloat && _isActive()) {
                    _float();
                };
            };
        };

        var _onWindowResize = function() {
            if (_isActive()) {
                if (!_isFooterVisible && _isFloat) {
                    _unfloat();
                    _float();
                };
            } else {
                _unfloat();
                _isFloat = false;
            };
        };

        var _setFooterWaypoint = function(){
            $('#app-footer').waypoint('destroy');
            $('#app-footer').waypoint(_onFooterWaypoint, {offset: '130%'});
        };
        _setFooterWaypoint();
        $('.protocol').waypoint(_onProtocolWaypoint, {offset: -50});
        $(window).resize(_onWindowResize);

    })();

});
