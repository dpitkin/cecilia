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
});