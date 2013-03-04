(function(){
    var videoPlayerPlay=function(that){
        var parent=$(that).parent();
        var embed_link=parent.attr('embed_link').replace('https://','http://');
        var player='<div>'
            +'<iframe src="'+embed_link+'" width="'+$(that).width()+'" height="'+$(that).height()+'" frameborder="0"></iframe>'
        +'</div>';
        parent.before(player);
        parent.hide();
    };
    var videoPlaylistPlayerPlay=function(that){
    	var parent=$(that).parents('.video_playlist_player');
        var embed_link=parent.attr('embed_link').replace('https://','http://');
        var view_link=parent.attr('view_link');
        var playlist_id=parent.attr('data-playlist-id');
        var description=parent.attr('data-description');
        if (embed_link.length>0) {
            var title=parent.find('.video_title').text();
            var modal=$('#video_playlist_modal_'+playlist_id);
            modal.find('iframe').attr('src',embed_link);
            modal.find('.video_viewlink').attr('href',view_link).text(title);
            modal.find('.video_description').text(description);
            modal.bind('hide', function(){
                modal.find('iframe').attr('src','');
            });
            modal.modal('show');
        } else if (view_link.length>0) {
        	window.open(view_link);
        };
    };
    $('.video_player .video_playbtn').click(function(){
        videoPlayerPlay(this);
    });
    $('.video_playlist_player .video_playbtn').click(function(){
        videoPlaylistPlayerPlay(this);
    });    
    $('.video_playlist_player .video_playlink').click(function(){
        videoPlaylistPlayerPlay(this);
    });

})();


