function resolve(domain) {
  $.ajax({
    type: 'POST',
    url: "{% url 'resolve' %}",
    data: {
      domain: domain,
      csrfmiddlewaretoken: '{{ csrf_token }}'
    },
    datatype: 'json',
    success: function(data) {
      if (data.success) {
        $('.resolve[title="' + domain + '"]').html('<a href="' + data.url + '">' + data.ip + '</a>');
      } else {
        $('.resolve[title="' + domain + '"]').text(data.error);
      }
    }
  });
}
$(".resolve").on("click", function() {
  resolve($(this).attr('title'));
});
