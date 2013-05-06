/**
 * since it would be affective on every luckydraw admin page
 * need to do some conditional judgment to figure out what is now
 * @author Ace Han
 * 
 */
(function ($) {
	$(function(){
		var currentUrl = window.location.href.toString();	//toString to keep ie working...
		var lastSlug = currentUrl.slice(currentUrl.lastIndexOf('/', currentUrl.length-2)).replace(/\//g, '');
		if(parseInt(lastSlug)){
			//==================================================================
			// for edit page only
			//==================================================================
			// you could still activate them via javascript...
			$('.submit-row').children().hide();
			$.get('/lucky-draw/perm/restore/'
					, function(data, textStatus, jqXHR){
						if(!data){return;}	// return immediately
						
						$('.submit-row').append(data)
						.live('click', function(){
							return confirm('Are you sure?\nAll session info. about Lucky Draw would fallback to this snapshot');
						});
					});
			
			// might as well do here the link here temporarily
			var interval = setInterval(function(){
				// since they are lazy loading
				if(!$('#id_current_winners_add_all_link').length){
					return;
				}
				$('#id_current_winners_add_all_link, #id_current_winners_remove_all_link').hide();
				// in order to make chooser-bg.gif disappear, too
				var cssStyle = {float: 'left', 
					    height: '50px',
					    margin: '10em 5px 0',
					    padding: 0,
					    width: '22px'};
				$('#id_current_winners_add_link').closest('.selector-chooser')
												.removeClass('selector-chooser')
												.css(cssStyle)
												.find('li')
												.hide();
				clearInterval(interval);
				interval = null;
			}, 300);
			
			//==================================================================
			// end of for edit page only
			//==================================================================	    
		}
	});
})(jQuery || django.jQuery);