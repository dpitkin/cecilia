/* Function is for customizing file input */
fileInputs = function() {
  var $this = $(this),
  $val = $this.val(),
  valArray = $val.split('\\'),
  newVal = valArray[valArray.length-1],
  $button = $this.siblings('.btn'),
  $fakeFile = $this.siblings('.file-holder');
  $afterText = $this.siblings('.after_photo');
  
  if(newVal !== '') {
    $button.text('Change Photo');
    if($fakeFile.length === 0) {
      // alert(newVal)
      $afterText.text('' + newVal + '');
    } else {
      $fakeFile.text(newVal);
    }
  }
};

$(document).ready(function(){

  $(".dropdown-toggle").dropdown();
  $('.datatable').dataTable({
    'aaSorting': [[0, 'desc' ]]
  });

  $("i.info_button-right").popover({
    placement:"right",
    trigger:"hover"
  });

  $('.file-wrapper input[type=file]').bind('change focus click',fileInputs);
});