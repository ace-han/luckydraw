/**
 * Slot as in jQuery Plugin 
 * 
 * @method init 					pleasae call $(selector).slot(opts) or $(selector).slot('init', opts) first 
 * @method enable(switchOrNot)
 * @method start
 * @method stop
 * @method reset(screenCssClass)    change the screen by css
 * @method destroy
 * @method isScrolling
 * @method isEnabled
 * @author Ace Han
 * 
 */
(function ($) {
	
	var PLUGIN_SETTING_KEY = PLUGIN_NAME = 'slot';
	var PLUGIN_INIT_SNAPSHOT_KEY = PLUGIN_SETTING_KEY+'-init-snapshot';
	var PLUGIN_ENABLE_KEY = PLUGIN_NAME + '-enabled';
	var PLUGIN_STARTED_KEY = PLUGIN_NAME + '-started';
	// adding PLUGIN_STOPPING_KEY for stop=>start if to trigger again at commenceDown when it's stilling scrolling
	var PLUGIN_STOPPING_KEY = PLUGIN_NAME + '-stopping';
	
	// class members' definition
	// leave them all configurable in an simple fashion, that is, $(selector).slot(opts)
	var DEFAULT_SETTINGS = {
		maxSpeed: 40
		, minSpeed: 4
		, step: 2
		, speed: 0
		, luckyClass: 'lucky'
		, screenHeight: 200
		, screenPieceCount: 5					//as least 3 pieces is needed, but tested and suggest to make it 5(test)
		, screenPieceCssClass: '' 
		, nextDisplay: function($elem){}
		// event
		// not using jQuery Event for simplification
		, onStart: function($slot){}								// return false to cancel start srolling
		, okayToStop: function($slot){}							// this usually for ajax call to ensure winner data
		, onCommenceDown: function($winnerPiece, $pieces){}		// for displaying lucky winner on commence down 
		, onStop: function($winnerPiece, $pieces){}	// display winner at last
		
		// belows are all calculated at runtime. Don't configure them at all 
		, $pieces: null
		, $winnerPiece: null
		, offsetTops: null
		, pieceHeight: null
		, outBoundaryY: null
		, inBoundaryY: null
		, winnerBoundaryY: null
		, scrollInterval: null
		, stopInterval: null
	};
	
	// special for annual party...
	var initScreenPieceDisplay = function(count){
		return '<div class="wrap"><span>' + (count+1) + '</span><br/></div>';
	}
	
	var initHtml = function(settings, autoFilled){
		// in order to avoid $pieces reference error in reset
		var itself = this; // here itself is the slot-screen for figuring out the total height, already jQuery Object
		//$('<style>.slot-screen-piece:first-child{margin-top:-'+settings.screenHeight+'px;}</style>').appendTo(itself);
		//$('<style/>').html('.slot-screen-piece:first-child{margin-top:-###px;}</style>').appendTo(itself.parent());
		var screenPiecesHtml = '';
		if(autoFilled){
			var height = Math.round(settings.screenHeight/2);
			for(var i=0; i<settings.screenPieceCount; ++i){
				screenPiecesHtml +=  '<div class="' +  settings.screenPieceCssClass 
				+ '" style="position:relative; height:' + height + 'px;">' + initScreenPieceDisplay(i) + '</div>';
			}
		} else {
			for(var i=0; i<settings.screenPieceCount; ++i){
				screenPiecesHtml +=  '<div class="' +  settings.screenPieceCssClass 
				+ '" style="position: relative;">' + initScreenPieceDisplay(i) + '</div>';
			}
		}
		// auto calculation for margin:first
		// init Block Auto-Margin
		var marginClass = 'slot-screen-piece' + new Date().getMilliseconds();
		if(!$.data(itself[0], 'marginClassName')){
			$.data(itself[0], 'marginClassName', marginClass);
			$('<style id="'+ marginClass +'">.' + marginClass + ':first-child{margin-top:0px;}</style>').appendTo(itself.parent());
		}
		// end of Block Auto-Margin
		settings.$pieces = itself.addClass('slot-screen')
				.css({height: settings.screenHeight
					, overflow: 'hidden'})
				.empty()
				.html(screenPiecesHtml)
				.children()
				.addClass(marginClass);
	};
	
	
	var initOffsetTops = function(settings){
		var itself = this; // here itself is the slot-screen for figuring out the total height, already jQuery Object
		// init top offset part
		var $pieces = settings.$pieces;
		// for accuracy sake, re-calculate pieceHeight even though it's already known 
		//settings.pieceHeight  = $pieces.eq($pieces.length-1).offset().top 
		//									- $pieces.eq($pieces.length-2).offset().top;
		settings.pieceHeight = $pieces.eq(0).outerHeight(true);
		// auto calculation for margin:first
		// Block Auto-Margin
		var styleDefinition = itself.parent().find('#' + $.data(itself[0], 'marginClassName'));
		
		// as least 3 pieces is needed, but tested and suggest to make it 5(test)
		// it's simply marginTop = ((screenPieceCount-3)/2)x + (x - (y-x)/2) = .5*screenPieceCount*x - .5y = (screenPieceCount*x -y)>>1
		//var pieceFragmentDeltaMargin = Math.floor((settings.screenHeight - settings.peiceHeight)/2);
		//var marginTop = settings.peiceHeight + pieceFragmentDeltaMargin;
		var marginTop = (settings.screenPieceCount*settings.pieceHeight - settings.screenHeight) >> 1;
		// fix IE could not change $element.text(...)
		styleDefinition.replaceWith(styleDefinition[0].outerHTML
				// floor(peiceHeight * floor(pieces.length/2)-.5)
				.replace('{margin-top:0px;}', '{margin-top:-'+ marginTop +'px;}'));
		// end of Block Auto-Margin
		
		var offsetTops = settings.offsetTops = [];
		$pieces.each(function(i, elem){
				offsetTops.push($(elem).offset().top);
		});
		settings.outBoundaryY = offsetTops[offsetTops.length-1] + settings.pieceHeight;
		settings.inBoundaryY = offsetTops[0];
		settings.winnerBoundaryY = offsetTops[Math.floor(offsetTops.length/2)];
	}
	
	var scroll = function(speed, settings){
		settings.$pieces.each(function(i, elem){
			var $e = $(elem);
			var nextTop = $e.offset().top + speed;
			if (nextTop >= settings.outBoundaryY){
				nextTop = settings.inBoundaryY + nextTop - settings.outBoundaryY;
				// change the display here
				settings.nextDisplay($e);
			}
			$e.offset({top: nextTop});
		});
	};
	
	var doStart = function(settings){
		settings.$winnerPiece = null;
		settings.speed = (settings.speed>=settings.maxSpeed)? settings.maxSpeed: (settings.speed+settings.step);
		scroll(settings.speed, settings);
	}
	
	var doStop = function(settings){
		settings.speed = (settings.speed<=settings.minSpeed)? settings.minSpeed: (settings.speed-settings.step);
		scroll(settings.speed, settings);
		if(settings.speed == settings.minSpeed){
			// the lucky winner should be already on the top of the slot screen
			// find out the lucky piece
			clearInterval(settings.scrollInterval);
			settings.$pieces.each(function(i, elem){
				$elem = $(elem);
				if(Math.abs($elem.offset().top - settings.inBoundaryY) <= settings.pieceHeight){
					settings.$winnerPiece = $elem.addClass(settings.luckyClass);
					return false;
				}
			});
			
			settings.onCommenceDown(settings.$winnerPiece, settings.$pieces);
			// ie did not support passing the parameter through...
			settings.scrollInterval = setInterval(function(){commenceDown(settings)}, 100);
		}
	}
	
	var commenceDown = function(settings){
		scroll(settings.minSpeed, settings);
		if(Math.abs(settings.$winnerPiece.offset().top - settings.winnerBoundaryY) <= settings.minSpeed){
			clearInterval(settings.scrollInterval);
			settings.scrollInterval = null;
			// BAD SOLUTION!!!
			$.removeData(settings.$winnerPiece.closest('.'+PLUGIN_NAME)[0], PLUGIN_STOPPING_KEY);
			settings.onStop(settings.$winnerPiece.removeClass(settings.luckyClass), settings.$pieces);
		}
	};
	
	var exportMethods = {
		init: function(options) {
			return this.each(function(){
				var itself = $(this);
				// save any self 
				var settings = $.data(this, PLUGIN_SETTING_KEY);
				if(settings){
					// already initialized, plz use reset or destroy method
					return;
				}
				// init part
				settings = $.extend({}, DEFAULT_SETTINGS, options);
				initHtml.call(itself, settings, !settings.screenPieceCssClass);
				initOffsetTops.call(itself, settings);		
				
				$.data(this, PLUGIN_SETTING_KEY, settings);
				// for reset
				$.data(this, PLUGIN_INIT_SNAPSHOT_KEY, $.extend(true, {}, settings));
				// enable/disable indicator, first set it enable...
				exportMethods.enable.call(itself, true);
			});
		}
		, enable: function(switchOrNot) {
			return this.each(function(){
				// providing a class for css customization
				$.data(this, PLUGIN_ENABLE_KEY, switchOrNot);
				$(this).toggleClass(PLUGIN_ENABLE_KEY, switchOrNot);
			});
		}
//		, disable: function() {
//			return this.each(function(){
//				$.data(this, PLUGIN_ENABLE_KEY, false)
//				$(this).removeClass(PLUGIN_ENABLE_KEY);
//			});
//		}
		, start: function() {
			return this.each(function(){
				var itself = $(this);
				if(!$.data(this, PLUGIN_ENABLE_KEY)
						|| $.data(this, PLUGIN_STARTED_KEY)
						|| $.data(this, PLUGIN_STOPPING_KEY)){
					return;
				}
				
				var settings = $.data(this, PLUGIN_SETTING_KEY);
				if(settings.$winnerPiece){
					settings.$winnerPiece.removeClass(settings.luckyClass);
					settings.$winnerPiece = null;
				}
				if(settings.onStart(itself) !== false){
					$.data(this, PLUGIN_STARTED_KEY, true);
					
					// ie did not support passing the parameter through...
					settings.scrollInterval = setInterval(function(){doStart(settings);}, 100);
				}
				
			});
		}
		, stop: function() {
			return this.each(function(){
				var itself = $(this);
				if(!($.data(this, PLUGIN_ENABLE_KEY)
						&& $.data(this, PLUGIN_STARTED_KEY))
						|| $.data(this, PLUGIN_STOPPING_KEY)){
					return;
				}
				var settings = $.data(this, PLUGIN_SETTING_KEY);
				// should stop function may insert here
				if(settings.okayToStop(itself) !== false){
					if(settings.stopInterval){
						clearInterval(settings.stopInterval);
						settings.stopInterval = null;
					}
					clearInterval(settings.scrollInterval);
					// mark it stop, however, it's still going to slow down for simplification sake
					$.removeData(this, PLUGIN_STARTED_KEY);
					$.data(this, PLUGIN_STOPPING_KEY, true);
					// ie did not support passing the parameter through...
					settings.scrollInterval = setInterval(function(){doStop(settings);}, 100);
				} else {
					// ie did not support passing the parameter through...
					settings.stopInterval = setInterval(function(){exportMethods.stop.call(itself);}, 500);
				} 
				
				
			});
		}
		// using css class the reshap
		, reset: function(screenPieceCssClass) {
			// not covering enable or disable, do it in a separated way
			return this.each(function(){
				var itself = $(this);
				var currentSettings = $.data(this, PLUGIN_SETTING_KEY);
				if(currentSettings.scrollInterval){
					clearInterval(currentSettings.scrollInterval);
					currentSettings.scrollInterval = null;
				}
				if(currentSettings.stopInterval){
					clearInterval(currenstSettings.scrollInterval);
					currenstSettings.scrollInterval = null;
				}
				if(currentSettings.$winnerPiece){
					currentSettings.$winnerPiece.removeClass(currentSettings.luckyClass)
					currentSettings.$winnerPiece = null;
					
				} 
				$.removeData(this, PLUGIN_STARTED_KEY);
				$.removeData(this, PLUGIN_STOPPING_KEY);
				
				$.extend(currentSettings, $.data(this, PLUGIN_INIT_SNAPSHOT_KEY));
				currentSettings.screenPieceCssClass = screenPieceCssClass || currentSettings.screenPieceCssClass;
				currentSettings.maxSpeed = 10;
				initHtml.call(itself, currentSettings, screenPieceCssClass || !currentSettings.screenPieceCssClass);
				if(screenPieceCssClass){
					// not to override the very initialized initSettings
					initOffsetTops.call(itself, currentSettings);
				}
			});
		}
		, desstroy: function() {
			return this.each(function(){
				$(this).empty();
				$.removeData(this, PLUGIN_SETTING_KEY)
				$.removeData(this, PLUGIN_INIT_SNAPSHOT_KEY);
			});
		}
		
		// not chaining method
		, isScrolling: function() {
			return $.data(this[0], PLUGIN_STARTED_KEY) || $.data(this[0], PLUGIN_STOPPING_KEY);
		}
		, isEnabled: function() {
			return $.data(this[0], PLUGIN_ENABLE_KEY);
		}
	};
	
	$.fn.slot = function( method ) {
	    if ( exportMethods[method] ) {
	    	return exportMethods[method].apply( this, Array.prototype.slice.call( arguments, 1 ));
	    } else if ( typeof method === 'object' || ! method ) {
	    	return exportMethods.init.apply( this, arguments );
	    } else {
	    	throw new Error( 'Method ' +  method + ' does not exist on jQuery.slot' );
	    }    
	  };
})(jQuery);