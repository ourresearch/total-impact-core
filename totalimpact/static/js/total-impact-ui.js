$.ajaxSetup ({
    cache: false
});
var ajax_load = "<img src='./static/img/ajax-loader.gif' alt='loading...' />";

parseImporterArgs = function(argStr){
    var args = argStr.split('-');
    var urlArgs = "id=" + args[0];
    if (args.length > 1) {
        urlArgs = urlArgs + "&type=" + args[1];
    }
    return urlArgs
}

// puts the textarea-entered ids in a format that addIdsToEditPane likes
parseTextareaArtifacts = function(str) {
    var ids = str.split("\n");
    var ret = [];
    for (i=0; i<ids.length; i++){
        var artifact = {};
        var thisId = ids[i];
        if (thisId.indexOf(":") > 0) {
            artifact.namespace = thisId.split(':')[0];
            artifact.id = thisId.substr(artifact.namespace.length + 1)
        }
        else {
            artifact.namespace = "unknown";
            artifact.id = thisId;
        }
        ret.push(artifact);
    }
    return ret;
}

addIdsToEditPane = function(returnedIds){
    if ($("#importers").width() > 340){
        $("#pullers")
            .animate({
                "margin-top": 0,
                left: 0
            }, 1000)
            .parent().siblings(" #edit-collection")
            .animate({
                width: "340px",
                "padding-right": "40px"
            }, 1000)
            .siblings("#importers")
            .animate({
                width: "340px"
            }, 1000, function(){
                return addIdsToEditPane(returnedIds);
            })
    }
    else {
        var len = returnedIds.length
        for (i=0; i<len; i++) {
            var namespace = returnedIds[i][0]
            var id = returnedIds[i][1];
            returnedIds[i] = "<li><a class='remove' href='#'>remove</a><span class='object-id'>";
            returnedIds[i] += "<span class='namespace'>"+namespace+": </span>";
            returnedIds[i] += "<span class='id'>"+id+"</span></span></li>";
        }
        $("ul#collection-list").append(
            $(returnedIds.join("")).hide().fadeIn(1000)
        );
        $("#artcounter")
//            .css("background-color", "#b20")
//            .animate({"background-color": "#eeeeee"}, 1000)
            .find("span.count")
            .text($("ul#collection-list li").size())
        return true;
    }

}

$(document).ready(function(){
    
    // report page stuff
    $('ul.metrics li').tooltip();
    $('a#copy-permalink').zclip({
        path:'ui/js/ZeroClipboard.swf',
        copy:$('#permalink a.copyable').text(),
        afterCopy:function(){
            $('a#copy-permalink').text('copied.');
        }
    });
    $('#about-metrics').hide();

    // show/hide stuff
    $('#importers ul li')
        .prepend('<span class="pointer">?</span>') // hack; these arrows should be entities, but that causes probs when replacing...
        .children("div")
        .hide();

    $('#importers ul li').children("a").click(function(){
        var arrow = $(this).siblings("span").text();
        arrow = (arrow == "?") ? "?" : "?";
        $(this).siblings("span").text(arrow);
        $(this).siblings("div").slideToggle();
    });

    $("div.quick-collection a").click(function(){
        $(this).parent().next().slideToggle();
    }).parent().next().hide();

    // click to remove object IDs in the edit pane
    $("ul#collection-list li").live("click", function(){
        $(this).slideUp(250, function(){$(this).remove();} );
        $("#artcounter span.count").text($("ul#collection-list li").size())
        return false;
    })
    $("a#clear-artifacts").click(function(){
        $("ul#collection-list").empty();
        $("#artcounter span.count").text("0")
        return false;
    });


    // use importers to add objects to the edit pane
    $("button.import-button").click(function(){
        var $thisDiv = $(this).parent();
        var idStrParts = $(this).attr("id").split('-');
        var providerName = idStrParts[0];
        var providerTypeQuery = "&type=" + $(this).siblings("input").attr("name");
        var providerIdQuery = "?query=" + $(this).siblings("input").val();

        if ($thisDiv.find("textarea")[0]) { // there's a sibling textarea
            addIdsToEditPane(parseTextareaArtifacts($thisDiv.find("textarea").val()));
        }
        else {
            $(this).hide().after("<span class='loading'>"+ajax_load+" Loading...<span>");
            $.get("./provider/"+providerName+"/memberitems"+providerIdQuery+providerTypeQuery, function(response,status,xhr){
                addIdsToEditPane(response);
                $thisDiv.find("span.loading")
                    .empty()
                    .append(
                        $("<span class='response'><span class='count'>"+response.length+"</span> added</span>")
                        .hide()
                        .fadeIn(500, function(){
                            $(this).delay(2000).fadeOut(500, function(){
                                $(this)
                                .parent()
                                .siblings("button")
                                .fadeIn(500)
                                .siblings("span.loading")
                                .remove()

                            })
                        })
                    )
            }, "json");
        }
    });



    // remove prepoluated values in form inputs
    $("textarea").add("input").focus(function(){
        if (this.defaultValue == this.value) {
            this.value = "";
        }
    }).blur(function(){
        if ($(this).val() == "") {
            $(this).val(this.defaultValue);
        }
    })

    // dialog for supported IDs
    $("div#manual-add p.prompt a").click(function(){
        TINY.box.show({url:'supported-ids.php'})
        return false;
    });

    // scroll down to recently shared reports
    $("#link-to-recently-shared").click(function(){
        $("html, body").animate({scrollTop: $(document).height()}, 1000)
            .find("#twitterfeed h4")
            .css("cssText", "background: transparent !important")
            .parent()
            .css("background", "#933")
            .animate({"background-color": "#eee"}, 1500, "linear")
        return false;
    });

    // table of contents
    if ($("#toc")[0]) {
        $('#toc').tocBuilder({type: 'headings', startLevel: 2, endLevel: 2, backLinkText: 'back to contents'});
    }



/* creating and updating reports
 * *****************************************************************************/
    showWaitBox = function(verb){
        verb = (typeof verb == "undefined") ? "Updating" : verb
        var $waitMsg = $("<div class='loading'></div")
            .append("<h2><img src='./static/img/ajax-loader-rev.gif' />"+verb+" your report now.</h2>")
            .append("<p>(Hang in there; it usually takes a few minutes...)</p>")

        TINY.box.show({
            html:$("<div>").append($waitMsg).html(),
            animate: false,
            close: false,
            removeable: false
        });
    }

    // creating a collection by submitting the object IDs from the homepage
    $("#id-form").submit(function(){
        var aliases = [];
        $("ul#collection-list span.object-id").each(function(){
           var thisAlias = [];
           thisAlias[0] = $(this).find("span.namespace").text()
           thisAlias[1] = $(this).find("span.id").text()
           aliases.push(thisAlias);
        });
        if (aliases.length == 0) {
            alert("Looks like you haven't added any research objects to the collection yet.")
            return false;
        } else {
            showWaitBox("Creating");
            $.post(
                './collection',
                {list: JSON.stringify(aliases), name: $("#name").val()},
                function(returnedData){
                    location.href="./collection/" +returnedData;
                });
            return false;
        }
    });

    // updating the collection from the report page
    $("#update-report-button").click(function(){
        showWaitBox();
        $.post(
            './update.php',
            {id: this.name},
            function(data){
                window.location.reload(false);
            });
        return false;
    })

    // mendeley quick-collections
    $("div.quick-collection div.response a").live("click", function(){
        showWaitBox();
        $.get(
            './update.php',
            this.href.replace(/[^?]+\?/, ""),
            function(data){
                location.href="./collection/" +data;
            });
        return false;

    });

});