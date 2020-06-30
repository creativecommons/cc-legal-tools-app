function orderby(sel) {
  var url = sel.options[sel.selectedIndex].value;
  if (url.indexOf('http') != 0) {
    url = "/worldwide/" + url;
  }
  location.href = url;
}
