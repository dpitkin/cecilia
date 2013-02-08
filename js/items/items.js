$(document).ready(function() {
  $('form').submit(function() {
    var err_msg = "";
    if($('#title').val().length == 0)
    {
      $('#title').parent().prev().addClass('error_text');
      err_msg += "Must have a title.<br/>";
    }
    if($('#description').val().length == 0)
    {
      $('#description').parent().addClass('error_text');
      err_msg += "Must have a description.<br/>";
    }
    if($('#price').val().length == 0)
    {
      $('#price').parent().prev().addClass('error_text');
      err_msg += "Must have a price.<br/>";
    }
    if(err_msg.length != 0)
      return false;
  });
});