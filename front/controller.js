$(document).ready(function () {

    //display speak messages
    eel.expose(DisplayMessage)
    function DisplayMessage(message) {
        $(".siri-message").text(message);
        if ($.fn.textillate) {
            $('.siri-message').textillate({ in: { effect: "fadeIn" } });
        }
    }

    //DISPLAY HOOD
    eel.expose(ShowHood)
    function ShowHood() {
        $("#oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
        $(".greeting-message").text($(".siri-message").text());
    }


});
