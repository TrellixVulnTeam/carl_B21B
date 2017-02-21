// Based on https://github.com/firebug/har-export-trigger/wiki/FAQ
// double curly braces so it can be loaded as a python string and then formated

// hardefined - set on initial synchronous call, used for instrumentation
window.hardefined = false;
//expcomplete - set by HAR.triggerExport callback, used for monitoring success 
window.expcomplete = "init";

function triggerExport() {{
    window.expcomplete = "About to trigger";
    var options = {{
        token: "test",
        getData: false,
        title: "{url}",
        jsonp: false,
        fileName: "{name}"
        }};
    HAR.triggerExport(options).then(result => {{window.expcomplete = "Done";}});

}};

// If HAR isn't yet defined, wait for the `har-api-ready` event.
// Otherwise trigger the export right away.
if (typeof HAR === "undefined") {{
    addEventListener('har-api-ready', triggerExport, false);
    window.hardefined = false;
}} else {{
    window.expcomplete = "Pre";
    triggerExport();
    window.hardefined = true;
}};

return window.hardefined;
