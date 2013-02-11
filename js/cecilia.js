$(document).ready(function(){

	$(".dropdown-toggle").dropdown();
	$('.datatable').dataTable({
    'aaSorting': [[0, 'desc' ]]
  });
	
	$("i.info_button-right").popover({
		placement:"right",
		trigger:"hover"
	});
  
});