$(document).ready(function () {

    //display speak messages
    eel.expose(DisplayMessage)
    function DisplayMessage(message) {
        $(".siri-message li:first").text(message);
        $('.siri-message').textillate('start');
    }

    //DISPLAY HOOD
    eel.expose(ShowHood)
    function ShowHood() {
        $("#oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
    }


});