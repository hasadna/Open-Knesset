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
        if (embed_link.length>0) {
	        $('.video_playlist_player_embed').remove();
	        $('.video_playlist_player').show();
	        var title=parent.find('.video_title').text();
	        var prev=parent.prev('.video_playlist_player_embed');
	        var player='<div class="video_playlist_player_embed">'
	            +'<iframe src="'+embed_link+'" width=400" height="300" frameborder="0"></iframe>'
	            +'<div><a class="video_viewlink" href="'+view_link+'" target="_blank">'+title+'</a></div>'
	        +'</div>';
	        player=$(player);
	        player.find('.video_viewlink').click(function(){
	            $('.video_playlist_player_embed').remove();
	            $('.video_playlist_player').show();
	        });
	        parent.before(player);
	        parent.hide();
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


