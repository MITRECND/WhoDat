$(document).ready(function() {

    //hide the search menu by default
    //search_toggle(0);

	$("#dialog").dialog({
            "width" : ($(window).width() * .8),
			/*"width": 800,*/
			"height": 640,
			"autoOpen": false 
	});


    var ajax_url = domains_url + key + "/" + value + "/?csrfmiddlewaretoken=" + csrf_token;
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

                        //Add expand icon
                        $("td:eq(0)", nRow).html('<span class="ui-icon ui-icon-circle-plus"></span>');

                        var domainName = aData[1];
                        $('td:eq(1)', nRow).html( '<a href="/pdns/' + encodeURIComponent(domainName) + '/">' 
                                                    + domainName + "</a>").attr('title', 'Click to Search Passive DNS');

                        var registrant = aData[2];
                        $('td:eq(2)', nRow).html( '<a href=/domains/registrant_name/' 
                                                    + encodeURIComponent(registrant) + '>' 
                                                    + registrant + '</a>').attr('title', 'Click to search by Registrant');

                        var reg_email = aData[3];
                        $('td:eq(3)', nRow).html( '<a href=/domains/contactEmail/' + encodeURIComponent(reg_email) 
                                                    + '>' + reg_email + '</a>').attr('title', 'Click to search by Email');


                        var telephone = aData[5];
                        $('td:eq(5)', nRow).html( '<a href=/domains/registrant_telephone/' 
                                                    + encodeURIComponent(telephone) + '>'
                                                    + telephone + '</a>').attr('title', 'Click to search by Telephone');


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

                                //Get a refrence to the new table
                                var dTab = $(this).parents("tr").next().find(".detailTable");

                                //Fill in the table with some details
                                get_domain(dTable.fnGetData(nTr)[1], dTab.find(".domain_quick"));

                                dTab.find(".fullDetail").on("click", function(){
                                    full($(this).attr('domainName'));
                                });

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

    var dTable ='<div class="detailTable">';

    dTable +=   '<div class="domain_details">';

    dTable +=   '<div class="title">';
    dTable +=   'More Details: ';
    dTable +=   '</div>';

    dTable +=   '<div class="domain_quick">';
    dTable +=   'Fetching Data';
    dTable +=   '</div>';


    dTable +=   '<div class="domain_full">';
    dTable +=   '<span class="link fullDetail" domainName="' + aData[1] + '">Click To Get Full Details</span>';
    dTable +=   '</div>';

    dTable +=   '</div>';

    dTable +=   '<div class="active_resolution">';

    dTable +=   '<div class="title">';
    dTable +=   'Active Resolution: ';
    dTable +=   '</div>';

    dTable +=   '<div class="active_res">';
    dTable +=   '<span class = "link resolve" title="Beware! Active Resolution live queries a DNS Server" domainName="' + aData[1] + '">Click Here to Actively Resolve</span>';
    dTable +=   '</div>';

    dTable +=   '</div>';

    dTable +=   '</div>';


    return dTable;
}

function full(domain) {
  var ep_url = domain_url + encodeURIComponent(domain) + "/";
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
	success: function(response) {
	  $("#dialog").dialog( "option", "title", domain);
	  if (response.success) {
		$("#dtext").empty();

		var result = response.data;
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
    $("#dialog").dialog("option", "position", "top")
	$("#dialog").dialog("open");
	}
  });
}


function get_domain(domain, target) {
  var ep_url = domain_url + encodeURIComponent(domain) + "/";
  $.ajax({
	type: 'GET',
	url: ep_url,
	datatype: 'json',
	success: function(response) {
	  if (response.success) {
		var result = response.data;

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
