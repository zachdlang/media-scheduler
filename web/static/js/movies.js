function followSearch() {
	if ($('#follow_search').val()) {
		getRequest(
			'/movies/search',  // movies_search
			{ search: $('#follow_search').val() },
			function(data) {
				compileHandlebars('search-result-template', '#follow_search_result', data);
				$('#follow_search_result').removeClass('hidden');
				$('.search-result').on('click', function() {
					followMovie($(this).data().moviedb_id);
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
			$('.watched_movie').on('click', function() {
				markWatched($(this).closest('.movie'));
			});
		}
	);
}

function followMovie(moviedb_id) {
	var data = {
		moviedb_id: moviedb_id,
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
	);
}

$('#followModal')
	.on('shown.bs.modal', function() {
		$('#follow_search').focus();
	})
	.on('hidden.bs.modal', function() {
		$('#follow_search').val('');
		$('#follow_search_result').addClass('hidden').empty();
	});

$('#follow_search_submit').on('click', followSearch);

$('#follow_search').on('keyup', function(e) {
	if (e.keyCode == 13) followSearch();
});

$(document).ready(getMovies);
