function updateQueryString(key, value, url) {
    if (!url) url = window.location.href;
    var re = new RegExp("([?&])" + key + "=.*?(&|#|$)(.*)", "gi"),
        hash;

    if (re.test(url)) {
        if (typeof value !== 'undefined' && value !== null)
            return url.replace(re, '$1' + key + "=" + value + '$2$3');
        else {
            hash = url.split('#');
            url = hash[0].replace(re, '$1$3').replace(/(&|\?)$/, '');
            if (typeof hash[1] !== 'undefined' && hash[1] !== null)
                url += '#' + hash[1];
            return url;
        }
    }
    else {
        if (typeof value !== 'undefined' && value !== null) {
            var separator = url.indexOf('?') !== -1 ? '&' : '?';
            hash = url.split('#');
            url = hash[0] + separator + key + '=' + value;
            if (typeof hash[1] !== 'undefined' && hash[1] !== null)
                url += '#' + hash[1];
            return url;
        }
        else
            return url;
    }
}


$(document).ready(function () {
    var loadingSymbol = $('#loading-statuses-symbol');
    var listContainer = $('#kikar-facebook-updates-ul');
    var offsetHandler = $('#statuses-more');
    var sectionDisplayElem = $('#kikar-statuses-section');

    var requestURL = '/kikar/get-statuses/';
    var kikarAPIPath = '/api/v1/';
    var kikarResourceName = 'facebook_status';
    var requestPath = kikarAPIPath + kikarResourceName + '/';

    var statusNumLimitPerRequest = 5;
    var defaultOrderBy = '-published';

    function requestAndAddStatuses() {

        requestURL = updateQueryString('request_path', requestPath, requestURL);
        requestURL = updateQueryString('filter', listContainer.data('filter'), requestURL);
        requestURL = updateQueryString('limit', statusNumLimitPerRequest, requestURL);
        requestURL = updateQueryString('offset', parseInt(offsetHandler.data('offset')), requestURL);
        requestURL = updateQueryString('order_by', defaultOrderBy, requestURL);
        //console.log(requestURL);
        loadingSymbol.show();
        $.ajax({
            url: requestURL, contentType: "application/json",
            success: function (data) {
                offsetHandler.data('offset', data.meta.offset + data.meta.limit);
                loadingSymbol.hide();
                data.objects.forEach(function (element, index, array) {
                    var source = $('#facebook-status-template').html();
                    var template = Handlebars.compile(source);
                    var html = template(element);
                    listContainer.append(html);
                });
            },
            error: function () {
                loadingSymbol.hide();
                listContainer.append("<p>התנצלותינו הכנה, ישנה תקלה בקטעינת הסטאטוס.</p>")
            }
        });
    }

    if (sectionDisplayElem.data('type') == 'member') {
        $.ajax({
            url: '/kikar/get-member/' + sectionDisplayElem.data('id'),
            contentType: "application/json",
            success: function (data) {
                console.log(data);
                if (data['main_feed'] == undefined) {
                    console.log('This Member does not have a facebook feed')
                } else if (data['name_he'] != sectionDisplayElem.data('test-name')) {
                    console.log('Apparent incompatibility between Kikar and OKnesset identifiers')

                } else {
                    sectionDisplayElem.show()
                }
            }
        });
    } else {
        sectionDisplayElem.show()
    }


    if (offsetHandler.length) {
        requestAndAddStatuses()
    }

    offsetHandler.on('click', function (event) {
        requestAndAddStatuses()
    });
});