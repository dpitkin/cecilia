$(document).ready(function() {
  $('form').submit(function() {
    if($('#title').val().length == 0)
    {
      $('#title').prev().addClass('error_text');
      return false;
    }
  });
});