function register_watch(object_id, object_type, watch_text, unwatch_text, follow_url, is_following_url) {
    jQuery.ajax({
        type: 'POST',
        url: is_following_url,
        data: {'id': object_id,
               'what': object_type},
        context: $('#watch'),
        success: function (data) {
            if (data == 'true') {
                document.is_watched = true;
            } else {
                document.is_watched = false;
            }
            
            if (document.is_watched) {
               $('#watch').html(unwatch_text);
            } else {
               $('#watch').html(watch_text);
            }
        },
        error:  function(request, textStatus, error) {
            document.is_watched = false;
        }
    });
     
    $('#watch').click( function () {
        if (document.is_watched) {
            jQuery.ajax({
                type: 'POST',
                url: follow_url,
                data: {'verb': 'unfollow',
                       'id': object_id,
                       'what': object_type},
                context: $('#watch'),
                success: function () {
                    document.is_watched = false;
                    this.html(watch_text);
                },
                error:  function(request, textStatus, error) {
                    var msg = $("#message_unknown").html()
                    $.jGrowl(msg, {life: 5000});
                    $('#message_login').show();
                }
            });
        }
        else {
            jQuery.ajax({
                type: 'POST',
                url: follow_url,
                data: {'verb': 'follow',
                       'id': object_id,
                       'what': object_type},
                context: $('#watch'),
                success: function () {
                    document.is_watched = true;
                    this.html(unwatch_text);
                },
                error:  function(request, textStatus, error) {
                    var msg = $("#message_login").html()
                    $.jGrowl(msg, {sticky: true});
                }
            });
        }
        return (false);
    })
}
