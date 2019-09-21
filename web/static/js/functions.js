function showLoading() { $('#loader').removeClass('hidden') }
function hideLoading() { $('#loader').addClass('hidden') }

function escapeHTML(str) {
	var escapes = {
		'&': '&amp;',
		'<': '&lt;',
		'>': '&gt;',
		'"': '&quot;',
		"'": '&#x27;'
	};
	return ('' + str).replace(/[&<>"']/g, function(match) {
		return escapes[match];
	});
}

function ajaxFailed(jqXHR) {
	// Only shows error message if not user aborted
	if (jqXHR.getAllResponseHeaders()) {
		showError('Internal error occurred. Please try again later.');
	}
}

function showSuccess(message) { showMessage(message, 'success') }
function showError(message) { showMessage(message, 'danger') }

function showMessage(message, flashClass) {
	if ($('.modal.in').length) elem = $('#modal_flash_div');
	else elem = $('#flash_div');
	elem.empty();
	
	$('<div class="alert">')
		.addClass('alert-' + flashClass)
		.text(message)
		.appendTo(elem);
}