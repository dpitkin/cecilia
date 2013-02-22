$(document).ready(function() {
  $('form').submit(function() {
    var error = false;
    if($('#title').val().length == 0)
    {
      $('#title').prev().addClass('error_text');
      error = true;
    }
    if($('#recipients').val().length == 0)
    {
      $('#recv_holder').prev().addClass('error_text');
      error = true;
    }
    //get rid of the leading comma
    var recip = $('#recipients');
    recip.val(recip.val().replace(',',''));
    if(error)
    return false;    
  });

  $('#recv_holder').change(function() {
    var sel = $(this).find('option:selected');
    var recv = $('#recv_results');
    recv.hide();
    recv.append(sel.text()+'<br/>');
    recv.slideDown(200);
    $('#recipients').val($('#recipients').val() + ',' + sel.attr('value'));
  });
});