$(document).ready(function(){
  $('form').submit(function() {
    var error_msg = "";
    if($('#first_name').val().length == 0)
    {
      error_msg += "Please fill out your first name<br/>";
      $('#first_name').prev().addClass('error_text');
    }
    if($('#last_name').val().length == 0)
    {
      error_msg += "Please fill out your last name<br/>";
      $('#last_name').prev().addClass('error_text');
    }
    if($('#nickname').val().length == 0)
    {
      error_msg += "Please fill out your nickname<br/>";
      $('#nickname').prev().addClass('error_text');
    }
    if(error_msg.length != 0)
      return false;
  });
  tinyMCE.init({
        mode : "specific_textareas",
        editor_selector : "readonlyRichText",
        readonly: true
  });
  tinyMCE.init({
        mode : "specific_textareas",
        editor_selector : "richtext"
  });
});