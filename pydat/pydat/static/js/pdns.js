$(document).ready(function() {

    //search_toggle(0);

    $('#pdns').tabs();

	$('#tab-DNSDB').tabs();
	$('#tab-PassiveTotal').tabs();

    $('.dnsres').dataTable(
				{
					"bJQueryUI": true,
					//"bAutoWidth": false,
					"oLanguage": {'sSearch': 'Filter:', 
                                  'sZeroRecords': 'No Records Found',
                                 },
                    "aoColumnDefs": [
                        {"sWidth": "15%", 'bSortable': false, 'aTargets': [-1]},
                    ],
					"sPaginationType": "full_numbers",
                    "sDom" : '<"H"lfirp>t<"F"lfip>',
					"iDisplayLength" : 50,
					"fnDrawCallback": function(oSettings) { 
						$(".resolve").on("click", function() {
                            $(this).removeClass('link');
                            $(this).off('click');
							resolve($(this).attr('domainName'), $(this));
						});
					}
				});

    var tabName = $(document.createElement('span'));
    tabName.text("PDNS" + direction + " Results");
    tabName.css('position', 'absolute');
    tabName.css('right', '20px');
    //tabName.css('color', 'white');
    tabName.css('font-size', '20px');
    tabName.css('top', '13px');
    $("#pdns-DNSDB").append(tabName);
    $("#pdns-PassiveTotal").append(tabName);
});
