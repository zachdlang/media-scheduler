function followSearch() {
	if ($('#follow_search').val()) {
		getRequest(
			'/shows/search',  // shows_search
			{ 'search':$('#follow_search').val() },
			function(data) {
				compileHandlebars('search-result-template', '#follow_search_result', data);
				$('#follow_search_result').removeClass('hidden');
				$('.search-result').on('click', function() {
					followShow(
						$(this).data().moviedb_id,
						$(this).data().name
					);
				});
			}
		);
	}
}

function getShows() {
	getRequest(
		'/shows/list',  // shows_list
		{},
		function(data) {
			compileHandlebars('show-template', '#content', data);
			$('#followed').text('('+data.shows.length+')');
			$('.remove_show').on('click', function() {
				var row = $(this).closest('.show');
				$(this).slideToggle(500);
				row.find('.confirm_remove').slideToggle(500);
			});
			$('.confirm_remove').on('click', function() {
				var tvshowid = $(this).closest('.show').data().tvshowid;
				unfollowShow(tvshowid);
			});
		}
	);
}

function unfollowShow(tvshowid) {
	postRequest(
		'/shows/unfollow',  // shows_unfollow
		{tvshowid: tvshowid},
		function() {
			showSuccess('Successfully removed.');
			getShows();
		}
	);
}

function followShow(moviedb_id, name) {
	postRequest(
		'/shows/follow',  // shows_follow
		{ moviedb_id: moviedb_id, name: name },
		function() {
			getShows();
			showSuccess('Successfully added.');
			$('#follow_search').val('').focus();
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

$(document).ready(getShows);