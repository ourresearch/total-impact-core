/*
* jQuery tocBuilder plugin, version 1.2.0.
* Go to http://proofbydesign.com/Resources/ for more information and documentation.
*
* Copyright (c) 2011 Rob Kent <rob.kent@proofbydesign.com>
* Licensed under the MIT License:
*   http://www.opensource.org/licenses/mit-license.php
*/
(function ($) {
    var props = {
        type: 'classes',
        insertBackLinks: true,
        backLinkText: 'Back',
        startLevel: 1,
        endLevel: 6,
        textCallback: null
    }

    var methods = {
        init: function (options) {
            // '$that' is the div that will contain the TOC. We are going to empty this destructively.
            var $that = this;

            jQuery.extend(props, options);

            if (props.type !== 'headings') {
                props.type = 'classes';
            }

            if (typeof (props.startLevel) !== 'number' || props.startLevel < 1) {
                props.startLevel = 1;
            }

            if (typeof (props.endLevel) !== 'number' || props.endLevel < 1) {
                props.endLevel = 6;
            }

            if (props.startLevel > props.endLevel) {
                var temp = props.endLevel;
                props.endLevel = props.startLevel;
                props.startLevel = temp;
            }

            $that.empty();
            var TOCTargetId = $that.attr('id') + "targetTOC";

            // Create a target for the 'Back' link (from a heading to the TOC).
            $("<a/>")
                .attr({
                    'id': TOCTargetId,
                    'name': TOCTargetId,
                    'class': 'tocBackTarget'
                }).appendTo($that);

            // If props.type=headings, select all Hx elements, otherwise select all elements with a tocEntry class; 
            // each tocEntry element should have a data-tocLevel attribute whose value should be a number.
            var selector;
            if (props.type === 'headings') {
                selector = ':header';
            }
            else {
                selector = '.tocEntry';
            }
            $(selector).each(function (index) {
                var $this = $(this);
                var level = 1;

                if (props.type === 'headings') {
                    // Use the number from the tag: h1, h2, etc.
                    level = parseInt(this.tagName.substring(1));
                }
                else {
                    // Use the value of the data-tocLevel attribute.
                    var test = $this.attr('data-tocLevel');
                    if (test !== undefined && parseInt(test) !== NaN) {
                        level = parseInt(test);
                    }
                }

                // Only process entries whose level is in range.
                if (level < props.startLevel || level > props.endLevel) return;

                var targetId = "toc_" + level + "_" + index;

                // Check if a previous TOC has already processed and stored the title. If so,
                // use that one so that we don't include our own back link in the text when creating
                // multiple TOCs with the same heading.
                var headingText = $this.text();
                if (headingText === undefined) {
                    // have we got a callback?
                    if (props.textCallback) {
                        headingText = props.textCallback($this);
                    }
                    else {
                        headingText = jQuery.trim($this.text());
                    }
                    $this.data('headingText', headingText);
                }

                // create an anchor and append it to the heading.
                var backLink = $("<a>" + props.backLinkText + "</a>")
                    .attr({
                        'class': 'tocBackLink',
                        'name': targetId,
                        'id': targetId,
                        'href': '#' + TOCTargetId,
                        'title': 'Go back to the table of contents'
                    });

                if (props.insertBackLinks !== true) {
                    // remove the text content of the backlink.
                    backLink.text('');
                }

                backLink.appendTo($this);

                // create a toc line at the correct level.
                var $TOCLine = $("<div class='TOCLine' />").attr('class', 'tocLevel' + level.toString());

                // create a toc entry and append it to the toc line div and append that to the toc div.
                var $entry = $("<a>" + headingText + "</a>")
                .attr({
                    'title': headingText,
                    'href': '#' + targetId,
                    'class': 'tocLink'
                })
                .appendTo($TOCLine)
                .parent()
                .appendTo($that);
            });

            return this.show();
        },

        disable: function (keepElement) {
            // emtpty the TOC element of all links and hide the element, unless keepElement=true.
            this.empty();
            if (props.insertBackLinks === true) {
                $("a.tocBackLink").remove();
            }
            if (keepElement !== true) {
                this.hide();
            }
            return this;
        },

        rebuild: function () {
            // clear and rebuild the TOC using the original options.
            this.tocBuilder('disable');
            this.tocBuilder('init');
            return this;
        }
    };

    $.fn.tocBuilder = function (method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.tocBuilder');
        }
    };
})(jQuery);