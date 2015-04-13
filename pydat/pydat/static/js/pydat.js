$(document).ready(function() {
    //Associate toggle with click
    $("#searchIcon").on("click", function() { search_toggle();}); 

    $("#" + active + "_link").addClass("tab_active");

    $("#pdnsr [name='key']").change(function(){
        if($(this).find("option:selected").val() == "name"){
            $(".form_rrtypes").removeClass("novis").show();
        }else{
            $(".form_rrtypes").addClass("novis");
        }
    });

    $(".search_form [name='fmt']").change(function(){
        //Limit only needs to be toggled for Domain JSON and LIST
         if ($(this).find("option:selected").val() != "normal"){
                 $(".form_limit").removeClass("novis").show();
         }else{
                 $(".form_limit").removeClass("novis").addClass("novis");
         }

        //Filtering should only be visible for List
        if($(this).find("option:selected").val() == "list"){
            $(this).parents('tbody').find('.form_filter').removeClass("novis").show();
        }else{
            $(this).parents('tbody').find('.form_filter').addClass("novis");
        }
    }); 

});


function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$.ajaxSetup({
    crossDomain: false, // obviates need for sameOrigin test
    beforeSend: function(xhr, settings) {
        var csrftoken = getCookie('csrftoken');
        if (!csrfSafeMethod(settings.type)) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

function search_toggle(duration){
        duration = typeof duration !== 'undefined' ? duration : 200;
        if ($("#button").hasClass('ui-icon-plus')){
                $("#button").removeClass('ui-icon-plus').addClass('ui-icon-minus');
                $("#searchBar").show(duration);
                //$(".domain_nonweb").show(); //Some weird bug that doesn't show the hidden fields
                //$(".pdns_nonweb").show();
        }else{
                $("#button").removeClass('ui-icon-minus').addClass('ui-icon-plus');
                $("#searchBar").hide(duration);
        }
}


function resolve(domain, target) {
  var ep_url = resolve_url + domain + "/"; 
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
	success: function(data) {
      var mspan = $(target);
	  if (data.success) {
        mspan.empty();

        var arTable = document.createElement('table');
        $(arTable).addClass('resolutionTable');

        for (i = 0; i < data.ips.length ; i++){
            var arRow = document.createElement('tr');
            var arCell = document.createElement('td');
            var anch = document.createElement('a');
            $(anch).attr("href", data.ips[i].url);
            $(anch).html(data.ips[i].ip); 

            $(arCell).append(anch);
            $(arRow).append(arCell);
            $(arTable).append(arRow);
            mspan.append(arTable);
        }
	  } else {
		mspan.text(data.error);
	  }
	}
  });
};



//Code for filtering delay taken from https://datatables.net/plug-ins/api
//Authors: Zygimantas Berziunas, Allan Jardine and vex
jQuery.fn.dataTableExt.oApi.fnSetFilteringDelay = function ( oSettings, iDelay ) {
    var _that = this;
 
    if ( iDelay === undefined ) {
        iDelay = 250;
    }
      
    this.each( function ( i ) {
        $.fn.dataTableExt.iApiIndex = i;
        var
            $this = this,
            oTimerId = null,
            sPreviousSearch = null,
            anControl = $( 'input', _that.fnSettings().aanFeatures.f );
          
            anControl.unbind( 'keyup' ).bind( 'keyup', function() {
            var $$this = $this;
  
            if (sPreviousSearch === null || sPreviousSearch != anControl.val()) {
                window.clearTimeout(oTimerId);
                sPreviousSearch = anControl.val(); 
                oTimerId = window.setTimeout(function() {
                    $.fn.dataTableExt.iApiIndex = i;
                    _that.fnFilter( anControl.val() );
                }, iDelay);
            }
        });
          
        return this;
    } );
    return this;
};
