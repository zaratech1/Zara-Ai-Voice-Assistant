$(document).ready(function () {
    if (typeof SiriWave !== "undefined") {
        new SiriWave({
            container: document.getElementById("siri-container"),
            width: 900,
            height: 200,
            style: "ios9",
            amplitude: 1,
            speed: 0.30,
            autostart: true
        });
    }

    function runCommand(command) {
        $("#oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        if (typeof eel === "undefined" || typeof eel.allCommands !== "function") {
            $(".greeting-message").text("Assistant connection is unavailable.");
            $("#oval").attr("hidden", false);
            $("#SiriWave").attr("hidden", true);
            return;
        }
        eel.allCommands(command)().catch(function (error) {
            console.error(error);
            $(".greeting-message").text("Assistant connection failed.");
            $("#oval").attr("hidden", false);
            $("#SiriWave").attr("hidden", true);
        });
    }

    $("#micBtn").click(function () {
        runCommand(null);
    });

    $("#chatBtn").click(function () {
        var command = $("#chatbox").val().trim();
        if (!command) return;
        $("#chatbox").val("");
        runCommand(command);
    });

    $("#chatbox").on("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            $("#chatBtn").click();
        }
    });

    $("#settingBtn").click(function () {
        $(".greeting-message").text("Try: open google, open Python on Wikipedia, or play music on YouTube.");
    });

});
