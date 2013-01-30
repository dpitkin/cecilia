
$(document).ready(function(){

	$(".dropdown-toggle").dropdown();
	$('.datatable').dataTable();
	
	$("i.info_button-right").popover({
		placement:"right",
		trigger:"hover"
	});
});