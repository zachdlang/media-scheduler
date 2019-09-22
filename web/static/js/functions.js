function showLoading() { $('#loader').removeClass('hidden'); }
function hideLoading() { $('#loader').addClass('hidden'); }

function compileHandlebars(templateId, destinationSelector, data) {
	var html = document.getElementById(templateId).innerHTML;
	var template = Handlebars.compile(html);
	$(destinationSelector).html(template(data));
}

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

function showSuccess(message) { showMessage(message, 'success'); }
function showError(message) { showMessage(message, 'danger'); }

function showMessage(message, flashClass) {
	if ($('.modal.in').length) elem = $('#modal_flash_div');
	else elem = $('#flash_div');
	elem.empty();
	
	$('<div class="alert">')
		.addClass('alert-' + flashClass)
		.text(message)
		.appendTo(elem);
}

function sendRequest(url, method, data, callbackFunc) {
	$.ajax({
		url: url,
		method: method,
		data: data
	}).done(function(data) {
		if (data.error) showError(data.error);
		else callbackFunc(data);
	}).fail(ajaxFailed);
}

function getRequest(url, data, callbackFunc) {
	sendRequest(url, 'GET', data, callbackFunc);
}

function postRequest(url, data, callbackFunc) {
	sendRequest(url, 'POST', data, callbackFunc);
}