$(document).ready(function () {
    $('.text').textillate({
        loop: true,
        sync: true,
        in: {
            effect: "bounceIn"
        },
        out: {
            effect: "bounceOut"
        },

    });



    //siri wave
    var siriWave = new SiriWave({
        container: document.getElementById("siri-container"),
        width: 900,
        height: 200,
        style: "ios9",
        amplitude: "1",
        speed: "0.30",
        autostart: true

    });

    // siri message animation

    //mic button click event

    $("#micBtn").click(function () {
        $("#oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        eel.allCommands()()
    });

});