function caretExpanded() {
	$('#outstanding').closest('.panel').find('.direction').addClass('flip');
}

function caretCollapsed() {
	$('#outstanding').closest('.panel').find('.direction').removeClass('flip');
}

$('.watched_show').on('click', function() {
	var row = $(this).closest('.show');
	postRequest(
		'/shows/watched',  // shows_watched
		{ 'episodeid':row.data().episodeid },
		function() {
			row.remove();
			$('.date, .outstanding-episodes').each(function() {
				if ($(this).find('.show').length <= 0) $(this).remove();
			});
		}
	);
});

$('#outstanding')
	.on('show.bs.collapse', caretExpanded)
	.on('hide.bs.collapse', caretCollapsed);