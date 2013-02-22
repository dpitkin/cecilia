$(document).ready(function() {
  $('#item_form').submit(function() {
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
    else if(isNaN(parseInt($('#price').val())))
    {
      $('#price').parent().prev().addClass('error_text');
      err_msg += "Must be a number.<br/>";
    }  
    if(err_msg.length != 0)
      return false;
  });
  
  $('#bid_form').submit(function() {
    if(isNaN(parseInt($('#bid').val())))
    {
      $('#bid').addClass('error_text');
      alert('Bid must be a number.');
      return false;
    }
  });
  
  $('#seller_rating').raty({
    score : 3,
    click: function(score, evt) {
      var redir = $('#redirect').text() + score;
      if(confirm('Are you sure you want to give a rating of ' + score + ' to this seller?'))
        window.location = redir;
    }
  });
  
  $('#rating_div').raty({
    score : 3,
    click: function(score, evt) {
      $('#rating').val(score);
    }
  });
  
  $.each($('.raty_rating'), function(index, value) {
    var r = $(this).data('rating');
    $(this).raty({
      readOnly: true,
      score : r
    });
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