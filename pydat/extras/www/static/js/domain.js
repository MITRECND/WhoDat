$(document).ready(function() {

    //hide the search menu by default
    //search_toggle(0);

	$("#dialog").dialog({
            "width" : ($(window).width() * .8),
			"height": 640,
			"autoOpen": false,
            "modal": true,
            "open": function(event, ui) {
                 $(this).parent().css('position', 'fixed');
            },
	});

    $("#statusDialog").dialog({
            "modal" : true,
            "height": 100,
            "width": 400,
            "autoOpen": false,
            "open": function(event, ui) {
                 $(this).parent().css('position', 'fixed');
            },
    });

    var ajax_url = dataTable_url + key + "/" + value + "/" + low_version + "/" + high_version + "/?csrfmiddlewaretoken=" + csrf_token;
    var dTable = $('.dnsres').dataTable(
				{
					"bJQueryUI": true,
                    "bProcessing": true,
                    "bServerSide": true,
                    "sAjaxSource": ajax_url,
					"bAutoWidth": false,
					"oLanguage": {'sSearch': 'Filter:', 
                                  'sProcessing' : 'Fetching Data', 
                                  'sZeroRecords': 'No Results Found',
                                 },
                    "sDom" : '<"H"lfirp>t<"F"lfip>',
                    "aoColumnDefs":[
						  {"sClass": "dtExpand", 'bSortable': false, 'aTargets': [0]},
						  //{'bSortable': false, 'aTargets': [6]},
						  {"sClass": "dnCell", 'aTargets': [1]},
                    ],
/*
					"aoColumns" : [
						  {"sClass": "dtExpand", 'bSortable': false},
						  {"sClass": "dnCell"},
                          null,
                          null,
                          null,
                          null
						],
*/
					"sPaginationType": "full_numbers",
                    "iDisplayLength" : 50,
                    //Called after ever row is written but not drawn
                    "fnRowCallback": function( nRow, aData, iDisplayIndex, iDisplayIndexFull) {

                        var oldVersion = '';
                        if (+aData[6] < +latest_version){
                            oldVersion = 'oldVersion';
                        }

                        //Add expand icon
                        $("td:eq(0)", nRow).html('<span class="ui-icon ui-icon-circle-plus"></span>');

                        var domainName = aData[1];
                        $('td:eq(1)', nRow).html( '<a href="/pdns_results/' + encodeURIComponent(domainName) + '/">'
                                                    + domainName + "</a>").attr('title', 'Click to Search Passive DNS').addClass(oldVersion);
                        var registrant = aData[2];
                        $('td:eq(2)', nRow).html( '<a href=/domains/registrant_name/' 
                                                    + encodeURIComponent(registrant) + '>' 
                                                    + registrant + '</a>').attr('title', 'Click to search by Registrant').addClass(oldVersion);

                        var reg_email = aData[3];
                        $('td:eq(3)', nRow).html( '<a href=/domains/contactEmail/' + encodeURIComponent(reg_email) 
                                                    + '>' + reg_email + '</a>').attr('title', 'Click to search by Email').addClass(oldVersion);

                        $('td:eq(4)', nRow).addClass(oldVersion);

                        var telephone = aData[5];
                        $('td:eq(5)', nRow).html( '<a href=/domains/registrant_telephone/' 
                                                    + encodeURIComponent(telephone) + '>'
                                                    + telephone + '</a>').attr('title', 'Click to search by Telephone').addClass(oldVersion);

                        $('td:eq(6)', nRow).addClass(oldVersion);

                    },
                    //Called after table is drawn
					"fnDrawCallback": function(oSettings) { 
                        //Add an onclick toggle for the expand cells
                        $('td.dtExpand span').on('click', function () {
                            var nTr = $(this).parents('tr')[0];
                            if (dTable.fnIsOpen(nTr)){ //Close the row
                                $(this).removeClass('ui-icon-circle-minus').addClass('ui-icon-circle-plus'); 
                                dTable.fnClose(nTr);
                            }else { //Open the row
                                $(this).removeClass('ui-icon-circle-plus').addClass('ui-icon-circle-minus');
                                dTable.fnOpen(nTr, fnFormatDetails(dTable, nTr), 'details');

                                //Get a reference to the new table
                                var dTab = $(this).parents("tr").next().find(".detailTable");
                                $(dTab).tabs();

                                var entry_version = dTable.fnGetData(nTr)[6];
                                //Fill in the table with some details
                                get_domain(dTable.fnGetData(nTr)[1], entry_version, dTab.find(".domain_quick"));
                                get_historical(dTable.fnGetData(nTr)[1], entry_version, dTab.find(".historyTable"));

                                //dTab.find(".fullDetail").on("click", function(){
                                //    full($(this).attr('domainName'), entry_version);
                                //});

                                dTab.find(".resolve").on("click", function() {
                                    //Disable Tooltip, onclick, and link class
                                    $(this).removeClass('link');
                                    $(this).tooltip( "option", "disabled", true );
                                    $(this).off("click");
                                    resolve($(this).attr('domainName'), $(this));
                                }).tooltip();
                            }
                        });

                        $('.dnsres').tooltip({ items: 'td[title]' });
                    }
				});
	
                dTable.dataTable().fnSetFilteringDelay(1000);

});



function fnFormatDetails ( oTable, nTr )
{
    var aData = oTable.fnGetData( nTr );

    curr_id = Math.random().toString(36).substring(8);
    hist_id = Math.random().toString(36).substring(8);

    var dTable ='<div class="detailTable">';

    dTable +=   '<ul>'
    dTable +=   '<li title="Examine Record Information"><a href="#' + curr_id + '">Record Details</a></li>'
    dTable +=   '<li title="Query Historical Records"><a href="#' + hist_id + '">Historical Records</a></li>'
    dTable +=   '</ul>'



    dTable +=   '<div id="' + curr_id + '"class="current_details">';

    dTable +=   '<div class="domain_details">';

    dTable +=   '<div class="title">';
    dTable +=   '&nbsp;';
    dTable +=   '</div>';

    dTable +=   '<div class="domain_quick">';
    dTable +=   'Fetching Data';
    dTable +=   '</div>';


    dTable +=   '<div class="domain_full">';
    dTable +=   '<span class="link fullDetail" domainName="' + aData[1] + '">Click To Get Full Details</span>';
    dTable +=   '</div>';

    dTable +=   '</div>'; //domain_details

    dTable +=   '<div class="active_resolution">';

    dTable +=   '<div class="title">';
    dTable +=   'Active Resolution: ';
    dTable +=   '</div>';

    dTable +=   '<div class="active_res">';
    dTable +=   '<span class = "link resolve" title="Beware! Active Resolution live queries a DNS Server" domainName="' + aData[1] + '">Click Here to Actively Resolve</span>';
    dTable +=   '</div>';

    dTable +=   '</div>'; //active_resolution

    dTable +=   '</div>'; //current_details

    dTable +=   '<div id="' + hist_id + '"class="history_details">';

    dTable +=   '<div class="historyTable">';
    dTable +=   'Fetching History';
    dTable +=   '</div>';

    dTable +=   '</div>'; //history_details

    dTable +=   '</div>'; //detailTable


    return dTable;
}

function full(domain, entry_version) {
  var ep_url = domain_url + encodeURIComponent(domain) + "/" + entry_version + "/";
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
    beforeSend: showStatusDialog,
    complete: hideStatusDialog,
	success: function(response) {
	  $("#dialog").dialog( "option", "title", domain);
	  if (response.success) {
		$("#dtext").empty();

		var result = response.data[0];
		var text = document.createElement('div');
        var dtab = document.createElement('table');

        $(dtab).addClass('fullDetailTable');
        $(text).append(dtab);
        $(dtab).html("<thead><th>Name</th><th>Value</th></thead><tbody></tbody>");
        var dtabb = $(dtab).find("tbody");

        //Sort the results in alphabetical order
        sort_arr = [];
        for (var key in result){
            sort_arr.push([key, result[key]]); 
        }
        sort_arr.sort(function(a, b) {
            return a[0].localeCompare(b[0]);
        });

		for (var i = 0; i < sort_arr.length; i++) {
            var drow = document.createElement('tr');
            var kcell = document.createElement('td');
            $(kcell).addClass('fdKey');
            var vcell = document.createElement('td');
            $(vcell).addClass('fdValue');

            $(kcell).html(sort_arr[i][0]);
            $(vcell).html(sort_arr[i][1]);

            $(drow).append(kcell).append(vcell);
            dtabb.append(drow);
		}
        
		$("#dtext").append(text);
	  } else {
		$("#dtext").append(response.error);
	  }
	$("#dialog").dialog("open");
	}
  });
}

function diff(domain, v1, v2) {
  var ep_url = domain_url + encodeURIComponent(domain) + "/diff/" + v1 + "/" + v2 + "/";
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
    beforeSend: showStatusDialog,
    complete: hideStatusDialog,
	success: function(response) {
	  $("#dialog").dialog( "option", "title", domain + " " + v1 + " -> " + v2);
	  if (response.success) {
		$("#dtext").empty();

		var result = response.data;
		var text = document.createElement('div');
        var dtab = document.createElement('table');

        $(dtab).addClass('diffTable');
        $(text).append(dtab);
        $(dtab).html("<thead><th>Entry</th><th>Version: " + v1 + "</th><th>Version: " + v2 + "</th></thead><tbody></tbody>");
        var dtabb = $(dtab).find("tbody");

        //Sort the results in alphabetical order
        sort_arr = [];
        for (var key in result){
            sort_arr.push([key, result[key]]); 
        }
        sort_arr.sort(function(a, b) {
            return a[0].localeCompare(b[0]);
        });

		for (var i = 0; i < sort_arr.length; i++) {
            var drow = document.createElement('tr');
            var kcell = document.createElement('td');
            $(kcell).addClass('fdKey');
            var vcell = document.createElement('td');
            $(vcell).addClass('fdValue');
            var vcell2 = document.createElement('td');
            $(vcell2).addClass('fdValue');

            $(kcell).html(sort_arr[i][0]);

            if (sort_arr[i][1] instanceof Array){
                $(vcell).html(sort_arr[i][1][0]);
                $(vcell2).html(sort_arr[i][1][1]);
                $(vcell).addClass('changed')
                $(vcell2).addClass('changed')
            }else{
                $(vcell).html(sort_arr[i][1]);
                $(vcell2).html(sort_arr[i][1]);
            }

            $(drow).append(kcell).append(vcell).append(vcell2);
            dtabb.append(drow);
		}
        
		$("#dtext").append(text);
	  } else {
		$("#dtext").append(response.error);
	  }
	$("#dialog").dialog("open");
	}
  });
}


function get_historical(domain, entry_version, target){
  var ep_url = domain_url + encodeURIComponent(domain) + "/";
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
    beforeSend: showStatusDialog,
    complete: hideStatusDialog,
	success: function(response) {
	  if (response.success) {
		var result = response.data;

        $(target).empty();


        var htable = document.createElement('table');
        $(htable).html("<thead><tr><th colspan=7>Historical Records</th></tr><tr><th>Version</th><th>Registrant</th><th>Email</th><th>Created</th><th>Telephone</th><th>Details</th><th>Diff</th></tr></thead>")  
        var hbody = document.createElement('tbody');
        $(htable).append(hbody);

        if (result.length == 1) { //Can't be zero
            //No Historical Records
            var hrow = document.createElement('tr');
            var hcell = document.createElement('td');
            $(hcell).attr('colspan', '7');
            $(hcell).addClass('zerohistory');
            $(hcell).html("No Historical Records Found");
            $(hrow).append(hcell);
            $(htable).append(hrow);
        }else{
            for(var i = 0; i < result.length; i++){
                var hrow = document.createElement('tr');
                var tdclass = "";

                if(+(result[i].Version) == +entry_version){
                    tdclass = "bold";
                }
                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                $(hcell).html(result[i].Version);
                $(hrow).append(hcell);

                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                $(hcell).html(result[i].registrant_name);
                $(hrow).append(hcell);

                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                $(hcell).html(result[i].contactEmail);
                $(hrow).append(hcell);

                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                $(hcell).html(result[i].standardRegCreatedDate);
                $(hrow).append(hcell);

                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                $(hcell).html(result[i].registrant_telephone);
                $(hrow).append(hcell);

                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                if(+entry_version == result[i].Version){
                    $(hcell).html('<span>&nbsp;</span>');
                }else{
                    $(hcell).html('<span class="link fullDetail" domainName="' + result[i].domainName + '">Click</span>');
                }
                $(hrow).append(hcell);

                var inner = "&nbsp;"
                if (i != 0){
                    inner = '<span class="link diff" domainName="' + result[i].domainName + '" version1="' + result[i - 1].Version + '" version2="' + result[i].Version + '">' + result[i - 1].Version + " > " + result[i].Version  + '</span>';
                }

                var hcell = document.createElement('td');
                $(hcell).addClass(tdclass);
                $(hcell).html(inner);
                $(hrow).append(hcell);


                $(htable).append(hrow);
            }
        }
        $(target).append(htable);

        var dTab = $(target).parents("tr").find(".detailTable");
        dTab.find(".fullDetail").on("click", function(){
            full($(this).attr('domainName'), entry_version);
        });
        dTab.find(".diff").on("click", function(){
            diff($(this).attr('domainName'), $(this).attr('version1'), $(this).attr('version2'));
        });
	  } else {
		$(target).html(response.error);
	  }
	}
  });
}


function get_domain(domain, entry_version, target) {
  var ep_url = domain_url + encodeURIComponent(domain) + "/" + entry_version + "/";
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
    beforeSend: showStatusDialog,
    complete: hideStatusDialog,
	success: function(response) {
	  if (response.success) {
		var result = response.data[0];
    
        $(target).empty();

        var reg_div = document.createElement('div');   
        $(reg_div).addClass('qdtable');
        $(reg_div).append(create_registrant_table(result));

        var adm_div = document.createElement('div');
        $(adm_div).addClass('qdtable');
        $(adm_div).append(create_adminContact_table(result));

        var date_div = document.createElement('div');
        $(date_div).addClass('qdtable');
        $(date_div).append(create_dates_table(result));

        $(target).append(reg_div);
        $(target).append(adm_div);
        $(target).append(date_div);
	  } else {
		$(target).html(response.error);
	  }
	}
  });
}

function create_registrant_table(raw_data){
    var registrant_p1 = ['name', 'organization', 'street1','street2','street3','street4']
    var registrant_p2 = ['city', 'state', 'postalCode', 'country']

    var regtab = document.createElement('table');
    $(regtab).html("<thead><tr><th>Registrant Contact</th></tr></thead>");
    var regbod = document.createElement('tbody');
    $(regtab).append(regbod);

    registrant_p1.forEach(function(piece){
        var index = "registrant_" + piece
        if (index in raw_data && (raw_data[index] != "")){
            var ptr= document.createElement('tr');
            var ptd= document.createElement('td');
            $(ptr).append(ptd);
            $(ptd).html(raw_data[index]);
            $(regbod).append(ptr);
        }
    });

    var ptr= document.createElement('tr');
    var ptd= document.createElement('td');
    $(ptr).append(ptd);

    registrant_p2.forEach(function(piece){
        var index = "registrant_" + piece
        if (index in raw_data && (raw_data[index] != "")){
            $(ptd).html($(ptd).html() + " " + raw_data[index]);
            $(regbod).append(ptr);
        }
    });

    return $(regtab);
}

function create_adminContact_table(raw_data){
    var adminContact_p1 = ['name', 'organization', 'street1','street2','street3','street4']
    var adminContact_p2 = ['city', 'state', 'postalCode', 'country']

    var admtab = document.createElement('table');
    $(admtab).html("<thead><tr><th>Administrative Contact</th></tr></thead>");
    var admbod = document.createElement('tbody');
    $(admtab).append(admbod);

    adminContact_p1.forEach(function(piece){
        var index = "administrativeContact_" + piece;
        if (index in raw_data && (raw_data[index] != "")){
            var ptr= document.createElement('tr');
            var ptd= document.createElement('td');
            $(ptr).append(ptd);
            $(ptd).html(raw_data[index]);
            $(admbod).append(ptr);
        }
    });

    var ptr= document.createElement('tr');
    var ptd= document.createElement('td');
    $(ptr).append(ptd);

    adminContact_p2.forEach(function(piece){
        var index = "administrativeContact_" + piece
        if (index in raw_data && (raw_data[index] != "")){
            $(ptd).html($(ptd).html() + " " + raw_data[index]);
            $(admbod).append(ptr);
        }
    });

    return $(admtab);
}

function create_dates_table(raw_data){
    var dates = ['CreatedDate', 'UpdatedDate', 'ExpiresDate'];

    var dtab = document.createElement('table');
    $(dtab).html("<thead><tr><th colspan=2>Significant Dates</th></tr></thead>");
    var dbod = document.createElement('tbody');
    $(dtab).append(dbod);

    dates.forEach(function(piece){
        var index = "standardReg" + piece;
        if (index in raw_data && (raw_data[index] != "")){
            var dtr = document.createElement('tr');
            var dti = document.createElement('td');
            var dtd = document.createElement('td');
            $(dtr).append(dti);
            $(dti).html(piece);
            $(dtr).append(dtd);
            $(dtd).html(raw_data[index]);
            $(dbod).append(dtr);
        }
    }); 

    return $(dtab);
}

var statusDialogStack = 0;

function showStatusDialog(){
	$("#statusDialog").dialog("open");
    statusDialogStack += 1; 
}

function hideStatusDialog(){
    statusDialogStack -= 1;
    if(statusDialogStack == 0){
        $("#statusDialog").dialog("close");
    }

}
