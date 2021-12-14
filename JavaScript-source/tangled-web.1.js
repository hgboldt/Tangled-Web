"use strict";

jQuery(document).ready(function($){

    //----------------------------------//
    // Insert search form into document //
    //----------------------------------//
    $('#search-menu').html(`<form>
<input type="hidden" id="gonk" name="gonk" value="" />
<table>
<tr><td><label for="surname">Surname:</label></td>
    <td colspan="3"><input id="surname" name="surname" type="text" size="30"/></td></tr>
<tr><td><label for="given">First name:</label></td>
    <td colspan="3"><input id="given" name="given" type="text" size="30"/></td></tr>
<tr><td><label for="place">Place:</label></td>
    <td colspan="3"><input id="place" name="place" type="text" size="30"/></td></tr>
<tr><td><label for="year-from">Period:</label></td>
    <td><input id="year-from" name="year-from" type="text"
               maxlength="4" size="4"/></td>
    <td><label for="year-to">to:</label></td>
    <td><input id="year-to" name="year-from" type="text"
               maxlength="4" size="4"/>
        <input id="email" name="email" type="text" /></td></tr>
<tr><td colspan="4"><button id="submit-search" class="tw-button">Submit Search</button>
    </td></tr>
<tr><td colspan="4"><span id="search-status"></span></td></tr>
</table>
</form>`);

    $('#gonk').val(myAjax.gonk);

    function parseQueryString(qs) {
        //
        // parseQueryString
        //
        var d = {};
        var q = qs.indexOf('?');
        if (q != -1) {
            qs = qs.substr(q+1);
        }
        var parts = qs.split('&');
        for(var i = 0; i < parts.length; i++) {
            var p = parts[i];
            var kv = p.split('=');
            d[kv[0]] = decodeURIComponent(kv[1]).replace(/\+/g, ' ');
        }
        return d;
    }

    function htmlEntities(str) {
        return (String(str).replace(/&/g, '&amp;')
                           .replace(/</g, '&lt;')
                           .replace(/>/g, '&gt;')
                           .replace(/"/g, '&quot;'));
    }

    window.onpopstate = function(event) {
        //
        // popstate event handler
        //
        $('#gimage').hide();
        var state = event.state;
        if (state) {
            if (state.type == 'indi') {
                fetch_indi(state.pid, state.page);
            }
            else if (state.type == 'search') {
                search_globs = state.globs;
                search_globs.last_search.gonk = $('#gonk').val();
                get_search_results(search_globs.last_search);
            }
        }
        else {
            go_home();
        }
    };

    $('.plnk').click(function() {
        //
        // Click on name of person
        //
        fetch_indi_push(get_pid(this));
        return false;
    });

    $('#home-button').click(function(){
        //
        // Click on "Home" icon
        //
        go_home_push();
    });

    function go_home_push() {
        //
        // Show home page and push history
        //
        $('#search-menu').hide();
        $.ajax({
            type: 'get',
            dataType: 'html',
            url: myAjax.ajaxurl,
            data: {'action': 'tangled_web_home',
                   'tab': myAjax.tab,
                   'show': myAjax.what_to_show},
            success: function(response){
                $('#tw-content').html(response);
                $('.cld-name').click(function() {
                    search_by_surname($(this).text());
                    return false;
                });
                $('.plnk').click(function() {
                    fetch_indi_push(get_pid(this));
                    return false;
                });
                window.history.pushState(null, 'Home', window.location.pathname);
                $('head title').html(myAjax.title);
            }
        });
    }

    function go_home() {
        //
        // Show home page
        //
        $('#search-menu').hide();
        $.ajax({
            type: 'get',
            dataType: 'html',
            url: myAjax.ajaxurl,
            data: {'action': 'tangled_web_home',
                   'tab': myAjax.tab,
                   'show': myAjax.what_to_show},
            success: function(response){
                $('#tw-content').html(response);
                $('.cld-name').click(function() {
                    search_by_surname($(this).text());
                    return false;
                });
                $('.plnk').click(function() {
                    fetch_indi_push(get_pid(this));
                    return false;
                });
                $('head title').html(myAjax.title);
            }
        });
    }

    $('#search-button').click(function(){
        //
        // Click on search button
        //

        if ($('#search-menu').is(':visible'))
        {
           $('#search-menu').hide();
           $('#search-status').hide();
           $('#search-status').html('');
        }
        else
        {
           $('#search-menu').show();
        }
    });

    $('#search-close').click(function(){
        //
        // click on search close button
        //
        $('#search-menu').hide();
    });

    $('#submit-search').click(function(){
        //
        // Click on "Submit Search" button
        //
        $('#search-menu').hide();

        if ($('#email').val()) {
            return false;
        }

        var urldata = { gonk: $('#gonk').val() };
        var surname = $('#surname').val();
        var given = $('#given').val();
        var place = $('#place').val();
        var year_from = $('#year-from').val();
        var year_to = $('#year-to').val();

        if (surname) {
            urldata.surname = surname;
        }
        if (given) {
            urldata.given = given;
        }
        if (place) {
            urldata.place = place;
        }
        if (year_from) {
            urldata.yearfrom = year_from;
        }
        if (year_to) {
            urldata.yearto = year_to;
        }
        search_globs.order_field = 'byear';
        search_globs.order_seq = 'A';
        urldata.orderby = search_globs.order_field;
        urldata.orderseq = search_globs.order_seq;
        get_search_results_push(urldata);
        return false;
    });

    $('.cld-name').click(function() {
        //
        // click on name in surname cloud
        //
        search_by_surname($(this).text());
        return false;
    });

    function search_by_surname(surname) {
        //
        // search_by_surname
        //
        search_globs.order_field = 'byear';
        search_globs.order_seq = 'A';
        var urldata = {action: 'tangled_web_search',
                       gonk: $('#gonk').val(),
                       surname: surname,
                       orderby: 'byear',
                       orderseq: 'A'};
        get_search_results_push(urldata);
    }

    var search_globs = {
        prev_seq: 'hdg-byear',
        order_field:  'byear',
        order_seq: 'A',
        last_search: null,
        search_results_count: null
    };

    function toggle_sequence(hdg) {
        //
        // toggle_sequence
        //
        var span = hdg.children('span');
        var hdgid = hdg.attr('id');
        if (hdgid == search_globs.prev_seq) {
            var seq = hdg.attr('seq');
            if (seq == 'A') {
                hdg.attr('seq', 'D');
                span.html('\u25BC');
                search_globs.order_seq = 'D';
            }
            else {
                hdg.attr('seq', 'A');
                span.html('\u25B2');
                search_globs.order_seq = 'A';
            }
        }
        else {
            var prev_elem = $('#' + search_globs.prev_seq);
            prev_elem.attr('seq', '');
            prev_elem.html('');
            hdg.attr('seq', 'A');
            span.html('\u25B2');
            search_globs.prev_seq = hdgid;
            search_globs.order_field = hdg.attr('fld');
            search_globs.order_seq = 'A';
        }
        go_search(0);
    }

    function go_search(offset) {
        //
        // go_search = Perform search
        //
        search_globs.last_search.offset = offset;
        search_globs.last_search.orderby = search_globs.order_field;
        search_globs.last_search.orderseq = search_globs.order_seq;
        search_globs.last_search.gonk = $('#gonk').val();
        get_search_results_replace(search_globs.last_search);
    }

    function get_search_results(urldata) {
        //
        // get_search_results - perform AJAX call to get results of search
        //
        urldata.action = 'tangled_web_search';
        urldata.table_id = myAjax.tab;
        $.ajax({
            type: 'get',
            dataType: 'json',
            url: myAjax.ajaxurl,
            data: urldata,
            success: function(response){
                output_search_results(response);
            },

            error: function(jqXhr, text, errorMessage) {
                $('#search-status').html(errorMessage);
                $('#search-status').show();
                $('#search-menu').show();
            }
        });
    }

    function get_search_results_push(urldata) {
        //
        // get_search_results - perform AJAX call to get results of search
        //
        urldata.action = 'tangled_web_search';
        urldata.table_id = myAjax.tab;
        $.ajax({
            type: 'get',
            dataType: 'json',
            url: myAjax.ajaxurl,
            data: urldata,
            success: function(response){
                output_search_results_push(response);
            },

            error: function(jqXhr, text, errorMessage) {
                $('#search-status').html(errorMessage);
                $('#search-status').show();
                $('#search-menu').show();
            }
        });
    }

    function get_search_results_replace(urldata) {
        //
        // get_search_results - perform AJAX call to get results of search
        //
        urldata.action = 'tangled_web_search';
        urldata.table_id = myAjax.tab;
        $.ajax({
            type: 'get',
            dataType: 'json',
            url: myAjax.ajaxurl,
            data: urldata,
            success: function(response){
                output_search_results_replace(response);
            },

            error: function(jqXhr, text, errorMessage) {
                $('#search-status').html(errorMessage);
                $('#search-status').show();
                $('#search-menu').show();
            }
        });
    }

    function output_search_results_replace(response) {
        //
        // output_search_results_replace
        //
        // Output results and update state
        //
        output_search_results(response);
        var state = {'type': 'search', 'globs': search_globs };
        window.history.replaceState(state, 'Search Results', window.location.href);
    }

    function output_search_results_push(response) {
        //
        // output_search_results_push
        //
        // Output results and push state
        //
        output_search_results(response);
        var state = {'type': 'search', 'globs': search_globs };
        window.history.pushState(state, 'Search Results', window.location.href);
    }

    function output_search_results(response) {
        //
        // output_search_results
        //
        $('#gonk').val(response.gonk);

        var search = response.search;
        search_globs.last_search = search;
        if (response.count) {
            search_globs.search_results_count = response.count;
        }
        else {
            response.count = search_globs.search_results_count;
        }

        var given_seq = '';
        var given_val = '';
        var surnm_seq = '';
        var surnm_val = '';
        var byear_seq = '';
        var byear_val = '';
        var bplac_seq = '';
        var bplac_val = '';
        var dyear_seq = '';
        var dyear_val = '';
        var dplac_seq = '';
        var dplac_val = '';
        if (search.orderby == 'given') {
            given_seq = search.orderseq;
            given_val = given_seq == 'A' ? '\u25B2' : '\u25BC';
        }
        else if (search.orderby == 'surname') {
            surnm_seq = search.orderseq;
            surnm_val = surnm_seq == 'A' ? '\u25B2' : '\u25BC';
        }
        else if (search.orderby == 'byear') {
            byear_seq = search.orderseq;
            byear_val = byear_seq == 'A' ? '\u25B2' : '\u25BC';
        }
        else if (search.orderby == 'bplace') {
            bplac_seq = search.orderseq;
            bplac_val = bplac_seq == 'A' ? '\u25B2' : '\u25BC';
        }
        else if (search.orderby == 'dyear') {
            dyear_seq = search.orderseq;
            dyear_val = dyear_seq == 'A' ? '\u25B2' : '\u25BC';
        }
        else if (search.orderby == 'dplace') {
            dplac_seq = search.orderseq;
            dplac_val = dplac_seq == 'A' ? '\u25B2' : '\u25BC';
        }

        var table = [];

        table.push('<table id="search-table">' + "\n" +
             '<tr class="th1"><th class="br" colspan="2">Name</th>' +
             '<th class="br" colspan="2">Birth</th>' +
             '<th colspan="2">Death</th></tr>' +
             '<tr class="th2"><th id="hdg-given" class="srch-hdg" fld="given" seq="' + given_seq +
             '">First' + given_val + '</th>' +
             '<th id="hdg-surnm" class="srch-hdg br" fld="surname" seq="' + surnm_seq +
             '">Surname' + surnm_val + '</th>' +
             '<th id="hdg-byear" class="srch-hdg" fld="byear" seq="' + byear_seq +
             '">Date' + byear_val + '</th>' +
             '<th id="hdg-bplac" class="srch-hdg br" fld="bplace" seq="' + bplac_seq +
             '">Place' + bplac_val + '</th>' +
             '<th id="hdg-dyear" class="srch-hdg" fld="dyear" seq="' + dyear_seq +
             '">Date' + dyear_val + '</th>' +
             '<th id="hdg-dplac" class="srch-hdg" fld="dplace" seq="' + dplac_seq +
             '">Place' + dplac_val + '</th></tr>' +
             "\n");

        var res_len = response.result.length;
        for (var i=0; i < res_len; i++)
        {
            var item = response.result[i];

            var given = (item.given || '');
            var surname = (item.surname || '');
            var bdate = (item.bdate || '');
            var bplace = (item.bplace || '');
            var ddate = (item.ddate || '');
            var dplace = (item.dplace || '');

            table.push('<tr class="search-row" pid="' + item.pid + '">' +
                       '<td class="search-td">' + htmlEntities(given) + '</td>' +
                       '<td class="search-td">' + htmlEntities(surname) + '</td>' +
                       '<td class="search-td">' + htmlEntities(bdate) + '</td>' +
                       '<td class="search-td">' + htmlEntities(bplace) + '</td>' +
                       '<td class="search-td">' + htmlEntities(ddate) + '</td>' +
                       '<td class="search-td">' + htmlEntities(dplace) + '</td></tr>' + "\n");
        }

        table.push('<tr class="search-nav">');

        var total_pages = Math.ceil(response.count / myAjax.searchlimit);
        var page;
        if (response.search.offset) {
            page = response.search.offset / myAjax.searchlimit + 1;
        }
        else {
            page = 1;
        }
        var more = (response.more == 1) ? '+' : '';

        table.push ('<td>Page&nbsp;' + page + '&nbsp;of&nbsp;' + total_pages + more + '</td>');

        table.push('<td colspan="5"><table class="srch-nav"><tr>');

        if (page > 1) {
            table.push('<td class="srch-go" offset="0">' +
                       '<img src="' + myAjax.baseurl + 'img/start.png"/></td> ');
            table.push('<td class="srch-go" offset="' + ((page-2)*myAjax.searchlimit) +
                       '"><img src="' + myAjax.baseurl + 'img/left.png"/></td>');
        }
        if (page > 2) {
            table.push('<td class="srch-go" offset="' + ((page-3)*myAjax.searchlimit) +
                       '">' + (page-2) + '</td>');
        }
        if (page > 1) {
            table.push('<td class="srch-go" offset="' + ((page-2)*myAjax.searchlimit) +
                       '">' + (page-1) + '</td>');
        }

        table.push('<td class="srch-sel">' + page + '</td>');

        if (page < (total_pages)) {
            table.push('<td class="srch-go" offset="' + (page*myAjax.searchlimit) +
                       '">' + (page+1) + '</td>');
        }
        if (page < (total_pages-1)) {
            table.push('<td class="srch-go" offset="' + ((page+1)*myAjax.searchlimit) +
                       '">' + (page+2) + '</td>');
        }
        if (page < total_pages) {
            table.push('<td class="srch-go" offset="' + ((page)*myAjax.searchlimit) +
                       '"><img src="' + myAjax.baseurl + 'img/right.png"/></td>');
            table.push('<td class="srch-go" offset="' + ((total_pages-1)*myAjax.searchlimit) +
                       '"><img src="' + myAjax.baseurl + 'img/end.png"/></td>');
        }

        table.push('</tr></table></td></tr>');
        table.push("</table>\n");

        $('#tw-content').html(table.join(''));
        $('#content')[0].scrollIntoView();

        $('.search-td').click(function() {
            var par = $(this).parent('tr');
            fetch_indi_push(par.attr('pid'));
        });

        $('.srch-hdg').click(function() {
            toggle_sequence($(this));
            return false;
        });
        $('.srch-go').click(function() {
            go_search($(this).attr('offset'));
            return false;
        });
    }

    function fetch_indi(pid, page='summary') {
        //
        // fetch_indi - Perform AJAX call to get information on one person
        //
        var fname = get_dirs_from_pid(pid) + '/' + pid + '.json';
        var famurl = '/' + myAjax.datadir + '/fam/' + fname;
        var indurl = '/' + myAjax.datadir + '/ind/' + fname;
        $.when($.ajax(famurl), $.ajax(indurl)).then(
            function(a1, a2) {
                    output_indi_results(a1[0], a2[0], page);
            });
    }

    function fetch_indi_push(pid) {
        //
        // fetch_indi - Perform AJAX call to get information on one person
        //
        var fname = get_dirs_from_pid(pid) + '/' + pid + '.json';
        var famurl = '/' + myAjax.datadir + '/fam/' + fname;
        var indurl = '/' + myAjax.datadir + '/ind/' + fname;
        $.when($.ajax(famurl), $.ajax(indurl)).then(
            function(a1, a2) {
                    output_indi_results_push(a1[0], a2[0]);
            });
    }

    function fetch_indi_replace(pid) {
        //
        // fetch_indi - Perform AJAX call to get information on one person
        //
        var fname = get_dirs_from_pid(pid) + '/' + pid + '.json';
        var famurl = '/' + myAjax.datadir + '/fam/' + fname;
        var indurl = '/' + myAjax.datadir + '/ind/' + fname;
        $.when($.ajax(famurl), $.ajax(indurl)).then(
            function(a1, a2) {
                    output_indi_results_replace(a1[0], a2[0]);
            });
    }

    function output_indi_results_replace(fam_info, ind_info) {
        //
        // output_indi_results_replace - output results and update state
        //
        output_indi_results(fam_info, ind_info);

        var state = {'type': 'indi',
                     'pid': ind_info.pid,
                     'dir': ind_info.dir,
                     'page': 'summary'};
        var newurl = window.location.pathname + '?p=' + ind_info.pid ;
        window.history.replaceState(state, '', newurl);
    }

    function output_indi_results_push(fam_info, ind_info) {
        //
        // output_indi_results_push - output results and push state
        //
        output_indi_results(fam_info, ind_info);

        var state = {'type': 'indi',
                     'pid': ind_info.pid,
                     'dir': ind_info.dir,
                     'page': 'summary'};
        var newurl = window.location.pathname + '?p=' + ind_info.pid;
        window.history.pushState(state, '', newurl);
    }

    function output_indi_results(fam_info, ind_info, page='summary') {
        //
        // output_indi_results
        //
        var names = ind_info.names;
        var primary_name = get_primary_name(names);
        var out = [];

        out.push(primary_name);

        if (ind_info.gallery) {
            var img_icon = '/' + myAjax.datadir + '/fam/' +
                           get_dirs_from_pid(ind_info.pid) + '/' +
                           ind_info.pid + '.big.jpg';
            var imgstr = '<img src="' + img_icon + '" class="icon-img">';
            out.push(imgstr);
        }

        out.push('<table id="ind-tabs"><tr>' +
                 '<td><div id="ind-summary" class="ind-tab-inactive">Family</div></td>' +
                 '<td><div id="ind-events" class="ind-tab-inactive">Timeline</div></td>');
        if (ind_info.notes) {
            out.push('<td><div id="ind-notes" class="ind-tab-inactive">Notes</div></td>');
        }
        if (ind_info.pedigree) {
            var ptitle = 'Pedigree' + (ind_info.pedigree.collapse ? ' *' : '');
            out.push('<td><div id="ind-pedigree" class="ind-tab-inactive">' + ptitle + '</div></td>');
        }
        if (ind_info.gallery) {
            out.push('<td><div id="ind-gallery" class="ind-tab-inactive">Album</div></td>');
        }
        out.push('<td><div id="ind-sources" class="ind-tab-inactive">Sources</div></td></tr></table>');

        out.push('<div id="summary-section" class="indi-content-hidden"></div>' +
                 '<div id="events-section" class="indi-content-hidden"></div>');
        if (ind_info.notes) {
            out.push('<div id="notes-section" class="indi-content-hidden"></div>');
        }
        if (ind_info.pedigree) {
            out.push('<div id="pedigree-section" class="indi-content-hidden"></div>');
        }
        if (ind_info.gallery) {
            out.push('<div id="gallery-section" class="indi-content-hidden"></div>');
        }
        out.push('<div id="sources-section" class="indi-content-hidden"></div>');

        var content = out.join('');
        $('#tw-content').html(content);

        $('#ind-summary').click(function(){
            select_page('summary', fam_info, ind_info, true);
        });
        $('#ind-events').click(function(){
            select_page('events', fam_info, ind_info, true);
        });
        $('#ind-notes').click(function(){
            select_page('notes', fam_info, ind_info, true);
        });
        $('#ind-pedigree').click(function(){
            select_page('pedigree', fam_info, ind_info, true);
        });
        $('#ind-gallery').click(function(){
            select_page('gallery', fam_info, ind_info, true);
        });
        $('#ind-sources').click(function(){
            select_page('sources', fam_info, ind_info, true);
        });

        select_page(page, fam_info, ind_info);
        $('#content')[0].scrollIntoView();
    }

    var format_function =
        {
            'summary': format_summary_section,
            'events': format_events_section,
            'notes': format_notes_section,
            'pedigree': format_pedigree_section,
            'gallery': format_gallery_section,
            'sources': format_sources_section
        };

    function select_page(page, fam_info, ind_info, update_state=false) {
        //
        // select_page - select page in tabbed view of data
        //
        if (update_state) {
            // Update state after tab change
            var state = window.history.state;
            state.page = page;
            var newurl = window.location.pathname + window.location.search;
            window.history.replaceState(state, '', newurl);
        }

        $('.ind-tab-active').attr('class', 'ind-tab-inactive');
        $('#ind-' + page).attr('class', 'ind-tab-active');
        $('.indi-content').attr('class', 'indi-content-hidden');

        var section = $('#' + page + '-section');
        if (!section.html()) {
            var section_html = format_function[page](fam_info, ind_info);
            if (section_html) {
                section.html(section_html);

                $('#' + page + '-section .plnk').click(function() {
                    fetch_indi_push(get_pid(this));
                    return false;
                });
                $('#' + page + '-section .note-toggle-button').click(function() {
                    toggle_note($(this));
                });
                $('#' + page + '-section .gimage').click(function() {
                    var img = $(this).attr('full');
                    var desc = $(this).attr('alt');
                    var ext = img.substr(img.lastIndexOf('.'));
                    $('#gimage-content').html('<img src="' + img + '" />');
                    $('#gimage-desc').html(desc);
                    $('#gimage').show();
                    $('#gimage-close').click(function(){
                        $('#gimage').hide();
                    });
                    $('#gimage-dl').click(function(){
                        var link = document.createElement('a');
                        link.style.display = 'none';
                        link.href = img;
                        link.download = desc + ext;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    });

                });
            }
        }
        section.attr('class', 'indi-content');
    }

    function get_primary_name(names) {
        //
        // get_primary_name - Get primary name from list of names
        //
        var names_len = names.length;
        var primi = 0;
        for (var i=0; i<names_len; i++) {
            if (names[i].prim == '1') {
                primi = i;
                break;
            }
        }

        var full_name = names[i].given + ' ' + names[i].surname;
        if ('nick' in names[i]) {
            full_name += ' (<i>' + names[i].nick + '</i>)';
        }
        var title = full_name + ' - ' + myAjax.title;
        $('head title').html(title);
        return '<p><span class="title-name">' + full_name + '</span> ' +
               fmt_cits(names[i].cits) + '</p>';
    }

    function format_summary_section(fam_info, ind_info) {
        //
        // format_summary_section
        //
        var i, j;
        var names = ind_info.names;
        var summary = ind_info.summary;

        var out = [];
        out.push('<h2>Family</h2>');


        out.push('<p>');

        var evstr = '';
        var sep = '';
        if (summary.btype == 'P') {
            evstr = '<span class="bold">Baptized:</span> ';
        }
        else if (summary.btype == 'B') {
            evstr = '<span class="bold">Born:</span> ';
        }
        evstr += fmt_date_place(summary.bdate, summary.bplace);
        if (evstr) {
            out.push(evstr);
            sep = '<br/>';
        }

        evstr = '';
        if (summary.dtype == 'B') {
            evstr = '<span class="bold">Buried:</span> ';
        }
        else if (summary.dtype == 'S') {
            evstr = '<span class="bold">Stillbirth:</span> ';
        }
        else if (summary.dtype == 'D') {
            evstr = '<span class="bold">Died:</span> ';
        }
        evstr += fmt_date_place(summary.ddate, summary.dplace);
        if (evstr) {
            out.push(sep + evstr + '</p>');
        }

        var names_len = names.length;
        if (names_len > 1) {
            out.push('<h3>Names</h3><ul class="names-list">');

            for (i=0; i<names_len; i++) {
                out.push('<li><span class="bold">' + names[i].nametype +
                         ':</span> ' + names[i].given + ' ' +
                         names[i].surname);
                if ('nick' in names[i]){
                    out.push(' (<i>' + names[i].nick + '</i>)');
                }
                var snametype = names[i].surnametype;
                if (snametype) {
                    out.push(' (' + snametype + ')');
                }
                out.push(fmt_cits(names[i].cits) + '</li>');
            }

            out.push('</ul>');
        }

        out.push('<h3>Family</h3>');

        out.push('<div id="ancestors">');
        var grands = get_grandparents(ind_info);

        out.push('<table id="anc-table"><tr>');

        if (grands) {
            out.push('<th colspan="2">Grandparents</th></tr><tr>');
            if (4 in grands) {
                out.push('<td>' + fmt_name(grands[4], true, true, false, true, true, true) + '</td>');
            }
            else {
                out.push('<td></td>');
            }
            if (6 in grands) {
                out.push('<td>' + fmt_name(grands[6], true, true, false, true, true, true) + '</td>');
            }
            else {
                out.push('<td></td>');
            }
            out.push('</tr><tr>');
            if (5 in grands) {
                out.push('<td>' + fmt_name(grands[5], true, true, false, true, true, true) + '</td>');
            }
            else {
                out.push('<td></td>');
            }
            if (7 in grands) {
                out.push('<td>' + fmt_name(grands[7], true, true, false, true, true, true) + '</td>');
            }
            else {
                out.push('<td></td>');
            }
            out.push('</tr><tr>');
        }

        out.push('<th colspan="2">Parents</th></tr><tr>');
        var adop;
        if ('dad' in fam_info.famc) {
            adop = '';
            if ('ado' in fam_info.famc.dad) {
                adop = '<br/><span class="adop">' + fam_info.famc.dad.ado + '</span>';
            }
            out.push('<td>' + fmt_name(fam_info.famc.dad, true, true, false, true, true, true)
                     + adop + '</td>');
        }
        else {
            out.push('<td></td>');
        }
        if ('mom' in fam_info.famc) {
            adop = '';
            if ('ado' in fam_info.famc.mom) {
                adop = '<br/><span class="adop">' + fam_info.famc.mom.ado + '</span>';
            }
            out.push('<td>' + fmt_name(fam_info.famc.mom, true, true, false, true, true, true)
                     + adop + '</td>');
        }
        else {
            out.push('<td></td>');
        }

        out.push('</tr></table>');

        out.push('</div>');

        out.push('<div id="siblings-section"></div>');
        format_siblings_section(fam_info, ind_info);

        if (fam_info.fams) {
            var fams = fam_info.fams;
            var numfams = fams.length;

            for (i=0; i<numfams; i++){
                var fam = fams[i];

                var spouse_type;
                if (ind_info.gdr == 'M') {
                    spouse_type = 'Wife';
                }
                else {
                    spouse_type = 'Husband';
                }

                out.push('<table id="anc-table"><tr>');
                out.push('<th colspan="2">' + spouse_type + '</th></tr><tr>');
                var details = get_marriage_details(ind_info, fam[0][0]);
                if (details) {
                    out.push('<td><img src="' + myAjax.baseurl + 'img/marr.png" style="float:left"/>');
                    var details_str = '<br/>' + details.date + '<br/>' + details.place;
                    out.push('<span class="bold">Married:</span> ' +
                             details_str + '</td>');
                }
                else {
                    out.push('<td></td>');
                }
                out.push('<td>' + fmt_name(fam[0], true, true, true, true, true, true) + '</td></tr><tr>');

                var children = fam[1];
                if (children) {
                    out.push('<th colspan="2">Children:</th>');
                    var numchildren = children.length;
                    for (j=0; j<numchildren; j++) {
                        if (j%2==0) {
                            out.push('</tr><tr>');
                        }
                        out.push('<td>' + fmt_name(children[j], true, true, false, true, true, true) + '</td>');
                    }
                }
                out.push('</tr></table>');
            }
        }

        if (ind_info.links) {
            out.push('<h3>External Links</h3><ul>');
            var links_len = ind_info.links.length;
            for (i=0; i<links_len; i++) {
                var link = ind_info.links[i];
                out.push('<li><a href="' + link[1] + '" target="_blank">' +
                         link[0] + '</a></li>');
            }
            out.push('</ul>');
        }

        return out.join('');
    }

    function format_siblings_section(fam_info, ind_info)
    {
        if ('mom' in fam_info.famc || 'dad' in fam_info.famc) {

            var parinfo = null;
            if ('mom' in fam_info.famc) {
                parinfo = fam_info.famc.mom;
            }
            else {
                parinfo = fam_info.famc.dad;
            }

            if (!parinfo) {
                return;
            }

            var parurl = '/' + myAjax.datadir + '/fam/' +
                         get_dirs_from_pid(parinfo.pid) + '/' +
                         parinfo.pid + '.json';

            $.ajax(parurl).done(function(mominfo){
                var i, j, len;
                var sibslist = null;

                // Look for family in which person is a child
                len = mominfo.fams.length;
                for (i=0; i<len && sibslist==null; i++) {
                    var children = mominfo.fams[i][1];
                    var num_children = children.length;
                    for (j=0; j<num_children; j++) {
                        if (children[j].pid == ind_info.pid) {
                            sibslist = children;
                            break;
                        }
                    }
                }

                var out = [];
                out.push('<table id="anc-table"><tr>');
                out.push('<th colspan="2">Siblings</th>');

                // Process siblings
                len = sibslist.length;
                var sibcnt = 0;
                for (i=0; i<len; i++) {
                    var sib = sibslist[i];
                    if (sibcnt%2==0) {
                        out.push('</tr><tr>');
                    }
                    if (sib.pid != ind_info.pid) {
                        sibcnt += 1;
                        out.push('<td>' + fmt_name(sib, true, true, false, true, true, true) + '</td>');
                    }
                }
                out.push('</tr></table>');

                if (sibcnt > 0) {
                    $('#siblings-section').html(out.join(''));
                    $('#siblings-section .plnk').click(function() {
                        fetch_indi_push(get_pid(this));
                        return false;
                    });
                }
            });
        }
    }

    function get_marriage_details(ind_info, spouseid) {
        var dates_len = ind_info.events.length;
        for (var i=0; i<dates_len; i++) {
            var events = ind_info.events[i];
            var events_len = events.events.length;
            for (var j=0; j<events_len; j++) {
                var event = events.events[j];
                if (event.event == 'Marriage' && event.role == 'Family') {
                    if ('spouse' in event && event.spouse[0] == spouseid) {
                        return {'date': ind_info.events[i].date,
                                'place': event.place};
                    }
                }
            }
        }
        return null;
    }

    function format_events_section(faminfo, ind_info) {
        //
        // format_events_section
        //
        var out = [];

        out.push('<h2>Timeline</h2>');
        out.push('<ul class="event-list">');

        var events = ind_info.events;
        var dates_len = events.length;
        for (var i=0; i<dates_len; i++) {
            out.push('<li><b>' + events[i].date + '</b><br/><ul>');
            var evs = events[i].events;
            var evs_len = evs.length;
            for (var j=0; j<evs_len; j++) {
                out.push('<li>' + handle_one_event(ind_info, (evs[j])) + '</li>');
            }
            out.push('</ul></li>');
        }
        out.push('</ul>');
        return out.join('');
    }

    var child_type = {'M': 'son', 'F': 'daughter'};
    var spouse_type = {'M': 'wife', 'F': 'husband'};
    var parent_type = {'M': 'father', 'F': 'mother'};

    function handle_one_event(ind_info, event) {
        //
        // handle_one_event - One event in the events section
        //
        var out = [];

        var rolestr = '';
        var cit_str = fmt_cits(event.cits);
        var participants_str = '';
        var descr_str = (event.desc) ? (event.desc + ' ') : '';

        if (event.role == 'Primary') {
            if (event.event == 'Birth' || event.event == 'Baptism') {
                var dadstr = (event.father) ? fmt_name(event.father, false, false, false) : '';
                var momstr = (event.mother) ? fmt_name(event.mother, false, false, false) : '';

                if (dadstr && momstr) {
                    participants_str = ' to parents ' + dadstr + ' and ' + momstr;
                }
                else if (dadstr) {
                    participants_str = ' to father ' + dadstr;
                }
                else if (momstr) {
                    participants_str = ' to mother ' + momstr;
                }
            }
        }
        else if (event.role == 'Family') {
            if (event.event.startsWith('Marriage')) {
                if (event.spouse) {
                    participants_str = ' to ' + fmt_name(event.spouse, false, false, false);
                }
            }
            else if (event.event == 'Divorce') {
                if (event.spouse) {
                    participants_str = ' from ' + fmt_name(event.spouse, false, false, false);
                }
            }
        }
        else if (event.role == 'Parent') {
            if (event.event.startsWith('Marriage')) {
                participants_str = 'of ' + format_husband_wife(event);
            }
            else {
                participants_str = 'of ' + child_type[event.child.gdr] + ' ' +
                                   fmt_name(event.child, false, false, false);
            }
        }
        else if (event.role == 'Spouse') {
            participants_str = 'of ' + spouse_type[ind_info.gdr] + ' ' +
                               fmt_name(event.spouse, false, false, false);
        }
        else if (event.role == 'Child') {
            if ('primary' in event) {
                participants_str = 'of ' + parent_type[event.primary.gdr] + ' ' +
                                   fmt_name(event.primary, false, false, false);
            } else {
                participants_str = 'of ' + format_parents(event);
            }
        }
        else if (event.role) {
            rolestr = event.role + ' for ';
            if (event.event == 'Marriage') {
                participants_str = 'of ' + format_husband_wife(event);
            }
            else {
                participants_str = 'of ' + fmt_name(event.primary, false, false, true);
            }
        }

        out.push(rolestr + '<b>' + event.event + '</b> ' + descr_str +
                 participants_str + cit_str);

        var sep = '';
        var wit_str = '';
        if (event.others) {
            var wits = event.others;
            var wit_len = wits.length;
            if (wit_len > 0) {
                for (var i = 0; i<wit_len; i++) {
                    wit_str += '<li>' + wits[i][0] + ': ' +
                            fmt_name(wits[i][1], false, false, true) + '</li>';
                }
            }
        }

        var attr_str = '';
        if ('attrs' in event) {
            attr_str = fmt_attr_list(event.attrs);
        }

        if (wit_str || attr_str) {
            out.push('<ul>');
            out.push(wit_str);
            out.push(attr_str);
            out.push('</ul>');
            sep = '';
        }
        else {
            sep = '<br>';
        }

        if (event.place) {
            out.push(sep + event.place);
            sep = '<br>';
        }


        return out.join('');
    }

    function format_husband_wife(event) {
        //
        // Format string of husband and wife
        //
        var hstr = '';
        if (event.husband) {
            hstr = fmt_name(event.husband, false, false, true);
        }
        var wstr = '';
        if (event.wife) {
            wstr = fmt_name(event.wife, false, false, true);
        }
        if (hstr && wstr) {
            return hstr + ' and ' + wstr;
        }
        if (hstr) {
            return hstr;
        }
        return wstr;
    }


    function format_parents(event) {
        //
        // Format string of parents
        //
        var hstr = '';
        if (event.husband) {
            hstr = fmt_name(event.husband, false, false, false);
        }
        var wstr = '';
        if (event.wife) {
            wstr = fmt_name(event.wife, false, false, false);
        }
        if (hstr && wstr) {
            return 'parents ' + hstr + ' and ' + wstr;
        }
        if (hstr) {
            return 'father ' + hstr;
        }
        return 'mother ' + wstr;
    }


    function format_gallery_section(faminfo, ind_info) {
        //
        // format_gallery_section
        //
        var out = [];
        out.push('<h2>Album</h2>');
        if (ind_info.gallery) {
            var gallerylen = ind_info.gallery.length;
            for (var i=0; i<gallerylen; i++) {
                out.push('<p>' + format_one_image(ind_info.gallery[i], true) + '</p>');
            }
        }
        return out.join('');
    }

    function format_one_image(image, show_date=false) {
        //
        // format_one_image
        //
        var imgdesc = image.dsc;
        var imgpath = get_dirs_from_pid(image.mid) + '/' + image.mid + image.ext;
        var imgpath_thm = imgpath;
        if (!imgpath_thm.endsWith('.jpg')) {
            var spl = imgpath_thm.split('.');
            spl[spl.length-1] = 'jpg';
            imgpath_thm = spl.join('.');
        }
        var imgpath = imgpath.replaceAll(' ', '%20')

        var full_image = '/' + myAjax.datadir + '/img/' + imgpath;
        var imgstr = '<img class="gimage" src="/' + myAjax.datadir + '/thm/' +
                     imgpath_thm + '" full="' + full_image +
                     '" alt="' + imgdesc + '"/>';
        imgstr += '<br/>' + imgdesc;

        if (show_date && image.dat) {
            imgstr += '<br/>' + image.dat;
        }
        return imgstr;
    }

    function format_sources_section(fam_info, ind_info) {
        //
        // format_sources_section
        //
        var out = [];
        out.push('<h2>Sources</h2><ol class="sources">');
        var nsect_count = 0;

        var len_sources = ind_info.sources.length;
        for (var i=0; i<len_sources; i++) {
            var src = ind_info.sources[i];
            out.push('<li>' + src.title);

            if ('attrs' in src) {
                out.push('<br/>' + fmt_attributes(src.attrs));
            }

            out.push('<ol class="citations">');
            var len_cits = src.cits.length;
            var sep='';
            for (var j=0; j<len_cits; j++) {
                out.push('<li>');
                sep = '';
                var cit = src.cits[j];
                if (cit.date) {
                    out.push(sep + '<b>Date:</b> ' + cit.date);
                    sep = '<br/>';
                }
                if (cit.page) {
                    out.push(sep + '<b>Page:</b> ' + cit.page);
                    sep = '<br/>';
                }
                if (cit.media) {
                    out.push(sep + '<b>Media:</b>');
                    var len_images = cit.media.length;
                    for (var k=0; k<len_images; k++) {
                        out.push('<br/>' + format_one_image(cit.media[k]));
                    }
                    sep = '<br/>';
                }
                if (cit.notes && cit.notes.length > 0) {
                    nsect_count += 1;
                    out.push(sep + '<b>Notes:</b>');
                    out.push(format_notes(cit.notes, nsect_count + 'Z'));
                    sep = '';
                }
                if ('attrs' in cit) {
                    out.push(sep + fmt_attributes(cit.attrs));
                }

                out.push('</li>');
            }
            out.push('</ol></li>');
        }
        out.push('</ol>');
        return out.join('');
    }

    function fmt_attributes(attrs) {
        var outstr = '';
        var sep = '';
        var attrs_length = attrs.length;
        for (var j=0; j<attrs_length; j++) {
            var attr = attrs[j];
            outstr += sep + '<b>' + attr.attr + ':</b> ';
            sep = '<br/>';
            if (attr.attr == 'URL') {
                outstr += '<a href="' + attr.val + '" target="_blank">' + attr.val + '</a>';
            }
            else {
                outstr += attr.val;
            }
            if ('cits' in attr) {
                outstr += fmt_cits(attr.cits);
            }

        }
        return outstr;
    }


    function fmt_attr_list(attrs) {
        var outstr = '';
        var attrs_length = attrs.length;
        for (var j=0; j<attrs_length; j++) {
            var attr = attrs[j];
            outstr += '<li>' + attr.attr + ': ';
            if (attr[0] == 'URL') {
                outstr += '<a href="' + attr.val + '" target="_blank">' + attr.val + '</a>';
            }
            else {
                outstr += attr.val;
            }
            if ('cits' in attr) {
                outstr += fmt_cits(attr.cits);
            }
            outstr += '</li>';

        }
        return outstr;
    }


    function fmt_cits(cits) {
        //
        // fmt_cits - format citation list, ie: [1a][3b]
        //
        if (!cits) {
            return '';
        }

        var citstr = ' <sup>';

        if (typeof cits === 'string' || cits instanceof String) {
            cits = cits.split(',');
        }

        var num_cits = cits.length;
        for (var i=0; i<num_cits; i++) {
            citstr += '[' + cits[i] + ']';
        }

        return citstr + '</sup>';
    }

    function format_pedigree_section(faminfo, ind_info) {
        //
        // format_pedigree_section
        //

        var ped = ind_info.pedigree;
        if (!ped) {
            return null;
        }


        var pedigree = ped.pedigree;
        var len_pedigree = pedigree.length;
        if (len_pedigree == 0) {
            return null;
        }

        var out = [];
        out.push('<h2>Pedigree</h2>');

        if (ped.collapse) {
            out.push('<p><b>* Pedigree Collapse. Scroll down for details.</b></p>');
        }

        out.push('<table class="ped-table"><tr><td>');

        var prevnum = 0;
        var rel_shown = false;
        var gen = 0;
        for (const [ancnum, pdetail] of Object.entries(pedigree)) {

            if (ancnum%2 == 0 || ancnum-1 != prevnum) {
                var cl = '';
                var g = Math.floor(Math.log2(ancnum));
                if (g > gen) {
                    gen = g;
                    cl = ' class="border-top"';
                }

                if (!rel_shown) {
                    out.push('</td><td>&nbsp;');
                }
                out.push('</td></tr><tr' + cl + '><td>');
            }
            else if (ancnum != 1) {
                out.push('<br/>');
            }
            prevnum = ancnum;

            rel_shown = false;

            if (typeof pdetail == 'number') {
                out.push(ancnum + ': ==> ' + pdetail);
            }
            else {
                out.push(ancnum + ': ' + fmt_name(pdetail[0], false, true, false));

                if (pdetail.length > 1) {
                    rel_shown = true;
                    out.push('</td><td><ul>');

                    var peditem_len = pdetail[1].length;
                    for (var j=0; j<peditem_len; j++) {
                        var ped_item = pdetail[1][j];
                        out.push('<li>');
                        var ancs_len = ped_item.length;
                        var plural = (ancs_len>2) ? 's' : '';

                        out.push(ped_item[0] + '<br/><b>Common ancestor' + plural + ':</b>');
                        for (var k=1; k<ancs_len; k++) {
                            var ancn = ped_item[k];
                            var anc = [ancn, pedigree[ancn][0]];
                            out.push('<br/>' + anc[0] + ': ' + fmt_name(anc[1]));
                        }
                        out.push('</li>');
                    }
                    out.push('</ul>');
                }
            }
        }

        if (!rel_shown) {
            out.push('</td><td>&nbsp;');
        }
        out.push('</td></tr></table>');
        return out.join('');
    }

    function format_notes_section(fam_info, ind_info) {
        //
        // format_notes_section
        //
        var out = [];
        out.push('<h2>Notes</h2>');
        out.push(format_notes(ind_info.notes, 'X'));
        return out.join('');
    }

    function format_notes(notes, prefix) {
        //
        // format_notes - Format a list of notes.
        //
        // The prefix is a character to provide unique id's for the notes
        // in the list.
        //
        if (!notes) {
            return null;
        }

        var len_notes = notes.length;
        if (len_notes == 0) {
            return null;
        }

        var note_count = 0;

        var out = [];
        for (var i=0; i<len_notes; i++) {
            var note = notes[i];
            var note_text = note.text;
            var note_first = note_text.split('<br')[0];
            if (note_first.length > 80) {
                note_first = note_first.substr(0,80) + '...';
            }

            note_count += 1;
            out.push('<div class="note"><b>' + note.type + '</b><br/>' +
                     '<div class="note-toggle-button" hid="N' + prefix + note_count +
                           '" sid="M' + prefix + note_count + '" show="first">' +
                           '<img src="' + myAjax.baseurl + 'img/expand-more.png"/></div>' +
                     '<div id="N' + prefix + note_count +
                        '" class="note-first">' + note_first + '</div>' +
                     '<div id="M' + prefix + note_count +
                        '" class="note-full">' + note_text + '</div></div>');
        }

        return out.join('');
    }

    function toggle_note(note_element) {
        //
        // toggle_note - toggle between short and long views of the note
        //
        var showid = note_element.attr('sid');
        var hideid = note_element.attr('hid');
        $('#' + hideid).hide();
        $('#' + showid).show();

        if (note_element.attr('show') == 'first') {
            note_element.attr('show', 'full');
            note_element.html('<img src="' + myAjax.baseurl + 'img/expand-less.png"/>');
        }
        else {
            note_element.attr('show', 'first');
            note_element.html('<img src="' + myAjax.baseurl + 'img/expand-more.png"/>');
        }
        note_element.attr('sid', hideid);
        note_element.attr('hid', showid);
    }

    function get_grandparents(ind_info) {
        //
        // Return list of up to 4 grandparents
        //
        if (!('pedigree' in ind_info)) {
            return null;
        }

        var ped = ind_info.pedigree;
        if (!ped) {
            return null;
        }
        ped = ped.pedigree;
        var grands = {};
        var found = false;
        for (var i=4; i<=7; i++) {
            if (i in ped) {
                found = true;
                grands[i] = ped[i][0];
            }
        }

        if (found) {
            return grands;
        }
        return null;
    }

    function fmt_name(namelink, gendersym=false, dates=false,
                      rel=false, link=true, img=false, split=false) {
        //
        // fmt_name - format one name
        //
        // namelink: a dict with following elements:
        //      pid: gramps id
        //      sur: surname
        //      giv: given names
        //      gdr: gender
        //      dat: (opt) vital dates
        //      rel: (opt) relationship to primary person
        //      ico: (opt) '1': person has an icon
        //      ado: (opt) adoption
        // gendersym: if true, show a gender symbol
        // dates: if true, show the vital dates
        // rel: if true, show the relationship
        // link: if true, enable a link
        //

        if (!namelink || typeof namelink === 'string' || namelink instanceof String) {
            return '<i>unknown</i>';
        }

        var pid = namelink.pid;
        var datadir = get_dirs_from_pid(pid);

        var brk='';
        if (split) {
            brk = '<br/>';
        }

        var addstr = '';
        if (dates && 'dat' in namelink && namelink.dat) {
            addstr += ' (' + namelink.dat + ')';
        }

        if (rel && 'rel' in namelink && namelink.rel) {
            var reldet = namelink.rel;
            if (typeof reldet === 'string' || reldet instanceof String) {
                addstr += ' ' + brk + '(' + reldet + ')';
            }
            else {
                addstr += ' ' + brk + '(' + reldet[0] +
                          ' ' + fmt_name(reldet[1]) + ')';
            }
        }

        var genderstr = '';
        if (gendersym) {
            if (namelink.gdr == 'F') {
                genderstr = ' \u2640';
            }
            else {
                genderstr = ' \u2642';
            }
        }

        var classes = '';
        if (link && datadir) {
            classes += ' plnk';
        }

        var main_classes = 'person';
        var imgstr = '';
        var spn1 = '';
        var spn2 = '';
        if (img && 'ico' in namelink && namelink.ico != '') {
            var img_icon = '/' + myAjax.datadir + '/fam/' + datadir + '/' + pid + '.jpg';
            imgstr = '<img src="' + img_icon + '" class="icon-img">';
            split = true;
            main_classes += ' person-with-img';
            spn1 = '<span class="person-desc">';
            spn2 = '</span>';
        }

        if (datadir) {
            return '<span class="' + main_classes + '">' + imgstr + spn1 +
                   '<a class="' + classes + '" ' +
                   'href="' + window.location.pathname +
                   '?p=' + pid + '">' +
                   htmlEntities(namelink.giv) + ' ' +
                   htmlEntities(namelink.sur) + '</a>' +
                   genderstr + brk + addstr + spn2 + '</span>';
        }

        return '<span class="'+ main_classes + '">' + imgstr + spn1 +
               htmlEntities(namelink.giv) + ' ' +
               htmlEntities(namelink.sur) + genderstr + brk +
               addstr + spn2 + '</span>';
    }


    function fmt_date_place(date, place) {
        //
        // fmt_date_place - format the given date and place into a string
        //
        var dstr = '';
        var sep = '';
        if (date) {
            dstr += date;
            sep = '; ';
        }
        if (place) {
            dstr += sep + htmlEntities(place);
        }
        return dstr;
    }


    function get_pid(elem) {
        //
        // Get pid from this element
        //
        return parseQueryString($(elem).attr('href')).p;
    }


    var NUM_SUBDIRS = 20;

    function get_dirs_from_pid(pid) {
        //
        // determine directories for person id
        //
        var num = Number(pid.replace(/\D/g, ''));
        var dn1 = num % NUM_SUBDIRS;
        var dn2 = Math.floor(num/NUM_SUBDIRS) % NUM_SUBDIRS;
        var dir1 = String.fromCharCode('a'.charCodeAt(0) + dn1);
        var dir2 = String.fromCharCode('a'.charCodeAt(0) + dn2);
        return dir1 + '/' + dir2;
    }

    $('#tw-buttons').show();

    //-------------------------------------------------//
    // If a query string is specified, show that page  //
    //-------------------------------------------------//
    if (window.location.search) {
        var qstr = parseQueryString(window.location.search);
        if ('p' in qstr) {
            fetch_indi_replace(qstr.p);
        }
        else if ('oldid' in qstr && 'pid' in myAjax) {
                fetch_indi_replace(myAjax.pid);
        }
        else {
            go_home_push();
        }
    }

});
