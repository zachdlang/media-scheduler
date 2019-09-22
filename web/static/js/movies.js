function followSearch() {
	if ($('#follow_search').val()) {
		getRequest(
			'/movies/search',  // movies_search
			{ search: $('#follow_search').val() },
			function(data) {
				compileHandlebars('search-result-template', '#follow_search_result', data);
				$('#follow_search_result')
					.removeClass('hidden')
					.on('click', '.search-result', function() {
						followMovie($(this));
					});
			}
		);
	}
}

function getMovies() {
	getRequest(
		'/movies/list',  // movies_list
		{},
		function(data) {
			Handlebars.registerPartial('movielist', $('#movielist-partial').html());
			compileHandlebars('movie-template', '#content', data);
			$('#followed').text('(' + data.count + ')');
		}
	);
}

function followMovie(elem) {
	var data = {
		moviedb_id: elem.data().moviedb_id,
		name: elem.data().name,
		releasedate: elem.data().releasedate
	};

	postRequest(
		'/movies/follow',  // movies_follow
		data,
		function() {
			getMovies();
			showSuccess('Successfully added.');
			$('#follow_search').val('').focus();
		}
	);
}

function removeEmptyDates() {
	$('.date').each(function() {
		if ($(this).find('.movie').length <= 0) $(this).remove();
	});
}

function markWatched(elem) {
	postRequest(
		'/movies/watched',  // movies_watched
		{ movieid: elem.data().movieid },
		function() {
			elem.remove();
			removeEmptyDates();
		}
	)
}

$('#followModal').on('shown.bs.modal', function() {
	$('#follow_search').focus();
});

$('#followModal').on('hidden.bs.modal', function() {
	$('#follow_search').val('');
	$('#follow_search_result').addClass('hidden').empty();
});

$('#follow_search_submit').on('click', followSearch);

$('#follow_search').on('keyup', function(e) {
	if (e.keyCode == 13) followSearch();
});

$('#content').on('click', '.watched_movie', function() {
	markWatched($(this).closest('.movie'));
});

$(document).ready(getMovies);
