"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useVoiceEngine = useVoiceEngine;
var react_1 = require("react");
var useVoiceSocket_1 = require("@/hooks/useVoiceSocket");
var useVoiceRecorder_1 = require("@/hooks/useVoiceRecorder");
var useSpeech_1 = require("@/hooks/useSpeech");
var intentService_1 = require("@/services/intentService");
var elderStore_1 = require("@/store/elderStore");
var authStore_1 = require("@/store/authStore");
function useVoiceEngine(options) {
    var _a;
    if (options === void 0) { options = {}; }
    var user = (0, authStore_1.useAuthStore)().user;
    var store = (0, elderStore_1.useElderStore)();
    var _b = (0, react_1.useState)('idle'), voiceState = _b[0], setVoiceState = _b[1];
    var _c = (0, react_1.useState)(false), continuousMode = _c[0], setContinuousMode = _c[1];
    var continuousModeRef = (0, react_1.useRef)(false);
    var processingRef = (0, react_1.useRef)(false);
    var _d = (0, react_1.useState)(''), transcript = _d[0], setTranscript = _d[1];
    var _e = (0, react_1.useState)(''), liveResponse = _e[0], setLiveResponse = _e[1];
    var _f = (0, react_1.useState)('disconnected'), connectionStatus = _f[0], setConnectionStatus = _f[1];
    var _g = (0, react_1.useState)(null), voiceError = _g[0], setVoiceError = _g[1];
    var addChatMessage = store.addChatMessage, reminders = store.reminders, updateReminderStatus = store.updateReminderStatus, addStars = store.addStars, addMoodEntry = store.addMoodEntry, toggleDevice = store.toggleDevice, triggerEmergency = store.triggerEmergency, smartDevices = store.smartDevices, vitals = store.vitals, checkIn = store.checkIn, updateCheckIn = store.updateCheckIn, completeCheckIn = store.completeCheckIn, familyContacts = store.familyContacts, initiateCall = store.initiateCall, cancelCall = store.cancelCall, endCall = store.endCall, callState = store.callState, gameSession = store.gameSession, startGame = store.startGame, answerGame = store.answerGame, endGame = store.endGame, playMusic = store.playMusic, toggleMusicPlayback = store.toggleMusicPlayback, nextTrack = store.nextTrack, prevTrack = store.prevTrack, stopMusic = store.stopMusic;
    var _h = (0, useSpeech_1.useSpeechSynthesis)(), speak = _h.speak, browserSpeaking = _h.isSpeaking, cancelSpeech = _h.cancel, ttsSupported = _h.supported;
    var _j = (0, useVoiceSocket_1.useVoiceSocket)({
        onTranscript: function (payload) {
            setTranscript(payload.text);
        },
        onAgentChunk: function (payload) {
            setLiveResponse(function (previous) { return previous + payload.content; });
        },
        onAgentFinal: function (payload) {
            var finalText = payload.content;
            var aiMsg = {
                id: "msg-".concat(Date.now()),
                role: 'assistant',
                content: finalText,
                timestamp: new Date().toISOString(),
            };
            addChatMessage(aiMsg);
            setLiveResponse('');
            setVoiceState('speaking');
            if (!audioPlayer.isPlaying && ttsSupported) {
                speak(finalText, function () {
                    processingRef.current = false;
                    if (continuousModeRef.current)
                        restartListening();
                    else
                        setVoiceState('idle');
                });
            }
        },
        onConnectionStatus: function (status) {
            setConnectionStatus(status);
            if (status === 'connected' && continuousModeRef.current) {
                setVoiceState('listening');
            }
        },
        onError: function (payload) {
            setVoiceError(payload.message);
            setVoiceState('error');
        },
    }), socketStatus = _j.status, socketTranscript = _j.transcript, assistantDraft = _j.assistantDraft, socketError = _j.error, socketThinking = _j.isThinking, sendAudioChunk = _j.sendAudioChunk, sendUserMessage = _j.sendUserMessage, stopConversation = _j.stopConversation, connectVoiceSocket = _j.connect, disconnectVoiceSocket = _j.disconnect, audioPlayer = _j.audioPlayer;
    var _k = (0, useVoiceRecorder_1.useVoiceRecorder)({
        onChunk: sendAudioChunk,
        onError: function (message) {
            setVoiceError(message);
            setVoiceState('error');
        },
        chunkDurationMs: 500,
    }), isRecording = _k.isRecording, recorderError = _k.error, startRecorder = _k.start, stopRecorder = _k.stop;
    (0, react_1.useEffect)(function () {
        if (socketTranscript)
            setTranscript(socketTranscript);
    }, [socketTranscript]);
    (0, react_1.useEffect)(function () {
        if (connectionStatus === 'connected' && continuousModeRef.current) {
            setVoiceState('listening');
        }
        else if (connectionStatus === 'connecting') {
            setVoiceState('processing');
        }
    }, [connectionStatus]);
    (0, react_1.useEffect)(function () {
        connectVoiceSocket();
    }, [connectVoiceSocket]);
    var restartListening = (0, react_1.useCallback)(function () {
        if (continuousModeRef.current && !processingRef.current) {
            setTimeout(function () {
                if (continuousModeRef.current) {
                    startRecorder();
                    setVoiceState('listening');
                }
            }, 800);
        }
    }, [startRecorder]);
    var isListening = isRecording;
    var isSpeaking = browserSpeaking || audioPlayer.isPlaying;
    var speechError = voiceError || recorderError || socketError;
    var sttSupported = typeof window !== 'undefined' && !!((_a = navigator.mediaDevices) === null || _a === void 0 ? void 0 : _a.getUserMedia);
    var executeAction = (0, react_1.useCallback)(function (result) {
        var _a, _b, _c, _d, _e, _f, _g, _h;
        var action = result.action;
        var data = result.data;
        // Navigation
        if (action === 'navigate_reminders' || action === 'show_reminders')
            (_a = options.onNavigate) === null || _a === void 0 ? void 0 : _a.call(options, 'reminders');
        else if (action === 'show_vitals' || action === 'navigate_health')
            (_b = options.onNavigate) === null || _b === void 0 ? void 0 : _b.call(options, 'vitals');
        else if (action === 'show_smart_home' || action === 'navigate_home')
            (_c = options.onNavigate) === null || _c === void 0 ? void 0 : _c.call(options, 'home');
        else if (action === 'navigate_companion' || action === 'navigate_talk')
            (_d = options.onNavigate) === null || _d === void 0 ? void 0 : _d.call(options, 'companion');
        else if (action === 'show_games' || action === 'navigate_games')
            (_e = options.onNavigate) === null || _e === void 0 ? void 0 : _e.call(options, 'games');
        else if (action === 'show_entertainment')
            (_f = options.onNavigate) === null || _f === void 0 ? void 0 : _f.call(options, 'companion');
        // Reminders
        if (action === 'mark_medicine_done') {
            var upcoming = reminders.find(function (r) { return r.status === 'upcoming' && r.type === 'medication'; });
            if (upcoming) {
                updateReminderStatus(upcoming.id, 'completed');
                addStars(5, 'Medication taken');
            }
        }
        else if (action === 'snooze_reminder') {
            var upcoming = reminders.find(function (r) { return r.status === 'upcoming'; });
            if (upcoming)
                updateReminderStatus(upcoming.id, 'snoozed');
        }
        else if (action === 'mark_all_reminders_done') {
            reminders.filter(function (r) { return r.status === 'upcoming'; }).forEach(function (r) { updateReminderStatus(r.id, 'completed'); addStars(2, "".concat(r.title, " completed")); });
        }
        // Mood
        if (action === 'log_mood') {
            var moodMap = { positive: 'happy', negative: 'sad', risk: 'anxious' };
            var rawSentiment = data === null || data === void 0 ? void 0 : data.sentiment;
            var sentiment = typeof rawSentiment === 'string' ? rawSentiment : undefined;
            var mappedMood = (_g = moodMap[sentiment]) !== null && _g !== void 0 ? _g : 'neutral';
            var rawUserText = data === null || data === void 0 ? void 0 : data.userText;
            var rawTriggers = data === null || data === void 0 ? void 0 : data.triggers;
            var note = typeof rawUserText === 'string' ? rawUserText : 'Voice mood entry';
            var triggers = Array.isArray(rawTriggers) ? rawTriggers : undefined;
            addMoodEntry({
                id: "m-".concat(Date.now()),
                mood: mappedMood,
                score: sentiment === 'positive' ? 8 : sentiment === 'negative' ? 3 : 5,
                note: note,
                timestamp: new Date().toISOString(),
                sentiment: (typeof sentiment === 'string' ? sentiment : 'neutral'),
                triggers: triggers,
            });
            addStars(3, 'Mood logged');
        }
        // Smart home
        if (action === 'toggle_lights') {
            var l = smartDevices.find(function (d) { return d.type === 'light'; });
            if (l)
                toggleDevice(l.id);
        }
        else if (action === 'toggle_lock') {
            var l = smartDevices.find(function (d) { return d.type === 'lock'; });
            if (l)
                toggleDevice(l.id);
        }
        else if (action === 'toggle_all_lights_on' || action === 'toggle_all_lights_off') {
            smartDevices.filter(function (d) { return d.type === 'light'; }).forEach(function (d) { return toggleDevice(d.id); });
        }
        // Emergency
        if (action === 'trigger_sos' || action === 'trigger_sos_critical') {
            triggerEmergency('voice');
            if (action === 'trigger_sos_critical') {
                familyContacts.filter(function (c) { return c.isPrimary || c.relationship === 'Caregiver'; }).forEach(function (c) {
                    addChatMessage({ id: "msg-alert-".concat(Date.now(), "-").concat(c.id), role: 'assistant', content: "\uD83D\uDEA8 Emergency alert sent to ".concat(c.name, " (").concat(c.relationship, ")"), timestamp: new Date().toISOString(), tags: ['emergency', 'alert'] });
                });
            }
        }
        // Calls
        var rawContactId = data === null || data === void 0 ? void 0 : data.contactId;
        if (action === 'initiate_call' && rawContactId && typeof rawContactId === 'string')
            initiateCall(rawContactId);
        if (action === 'cancel_call')
            cancelCall();
        if (action === 'retry_call' && callState.contactId)
            initiateCall(callState.contactId);
        // Hydration
        if (action === 'mark_hydration') {
            var h = reminders.find(function (r) { return r.type === 'hydration' && r.status === 'upcoming'; });
            if (h) {
                updateReminderStatus(h.id, 'completed');
                addStars(2, 'Hydration completed');
            }
        }
        // Check-in
        if (action === 'start_checkin')
            (_h = options.onCheckInStart) === null || _h === void 0 ? void 0 : _h.call(options);
        if (action === 'start_exercise')
            addStars(5, 'Exercise started');
        // === GAMES ===
        var rawGameType = data === null || data === void 0 ? void 0 : data.gameType;
        if (action === 'start_game' && typeof rawGameType === 'string') {
            startGame(rawGameType);
            addStars(2, 'Started a game');
        }
        if (action === 'end_game')
            endGame();
        // === MUSIC ===
        var rawGenre = data === null || data === void 0 ? void 0 : data.genre;
        if (action === 'play_music' && typeof rawGenre === 'string') {
            playMusic(rawGenre);
            addStars(2, 'Playing music');
        }
        if (action === 'toggle_music')
            toggleMusicPlayback();
        if (action === 'next_track')
            nextTrack();
        if (action === 'prev_track')
            prevTrack();
        if (action === 'stop_music')
            stopMusic();
    }, [reminders, smartDevices, familyContacts, callState, options.onNavigate, options.onCheckInStart]);
    var processInput = (0, react_1.useCallback)(function (text) {
        var _a, _b;
        setVoiceState('processing');
        processingRef.current = true;
        var userMsg = {
            id: "msg-".concat(Date.now()),
            role: 'user',
            content: text,
            timestamp: new Date().toISOString(),
        };
        addChatMessage(userMsg);
        if (socketStatus === 'connected') {
            sendUserMessage(text);
            return;
        }
        var result = (0, intentService_1.detectIntent)(text, { reminders: reminders, smartDevices: smartDevices, familyContacts: familyContacts, callState: callState, gameSession: gameSession });
        if (result.action === 'game_answer' && typeof ((_a = result.data) === null || _a === void 0 ? void 0 : _a.answer) === 'string') {
            var answer = result.data.answer;
            var skipped = Boolean((_b = result.data) === null || _b === void 0 ? void 0 : _b.skipped);
            var gameResult = answerGame(skipped ? '' : answer);
            var responseText = void 0;
            if (skipped) {
                responseText = gameResult.correctAnswer
                    ? "No worries! The answer was: ".concat(gameResult.correctAnswer, ". ").concat(gameResult.done ? "Game over! Your final score: ".concat(gameSession.score, "/").concat(gameSession.totalQuestions, ". \uD83C\uDF89") : "Let's try the next one!")
                    : "Skipped! Let's move on.";
            }
            else if (gameResult.correct) {
                responseText = "\u2705 Correct! Great job! ".concat(gameResult.done ? "\uD83C\uDF89 Game complete! Final score: ".concat(gameSession.score + 1, "/").concat(gameSession.totalQuestions, "! You earned ").concat((gameSession.score + 1) * 3, " wellness stars!") : 'Here comes the next one!');
                if (gameResult.done)
                    addStars((gameSession.score + 1) * 3, 'Game completed');
            }
            else {
                responseText = "\u274C Not quite! The answer was: ".concat(gameResult.correctAnswer || 'unknown', ". ").concat(gameResult.done ? "Game over! Your score: ".concat(gameSession.score, "/").concat(gameSession.totalQuestions, ". Well played! \uD83C\uDF1F") : "Don't worry, let's try the next one!");
                if (gameResult.done)
                    addStars(Math.max(gameSession.score * 2, 1), 'Game completed');
            }
            var aiMsg_1 = {
                id: "msg-".concat(Date.now() + 1),
                role: 'assistant',
                content: responseText,
                timestamp: new Date().toISOString(),
                intent: 'game_answer',
                tags: ['game'],
            };
            addChatMessage(aiMsg_1);
            setVoiceState('speaking');
            if (ttsSupported) {
                speak(responseText, function () {
                    processingRef.current = false;
                    if (continuousModeRef.current)
                        restartListening();
                    else
                        setVoiceState('idle');
                });
            }
            else {
                processingRef.current = false;
                if (continuousModeRef.current)
                    restartListening();
                else
                    setVoiceState('idle');
            }
            return;
        }
        executeAction(result);
        var aiMsg = {
            id: "msg-".concat(Date.now() + 1),
            role: 'assistant',
            content: result.response,
            timestamp: new Date().toISOString(),
            intent: result.intent,
            tags: [result.intent],
        };
        addChatMessage(aiMsg);
        setVoiceState('speaking');
        if (ttsSupported) {
            speak(result.response, function () {
                processingRef.current = false;
                if (continuousModeRef.current)
                    restartListening();
                else
                    setVoiceState('idle');
            });
        }
        else {
            processingRef.current = false;
            if (continuousModeRef.current)
                restartListening();
            else
                setVoiceState('idle');
        }
    }, [addChatMessage, socketStatus, sendUserMessage, reminders, smartDevices, familyContacts, callState, gameSession, intentService_1.detectIntent, answerGame, addStars, ttsSupported, executeAction]);
    var startContinuous = (0, react_1.useCallback)(function () {
        setContinuousMode(true);
        continuousModeRef.current = true;
        cancelSpeech();
        processingRef.current = false;
        startRecorder();
        setVoiceState('listening');
    }, [cancelSpeech, startRecorder]);
    var stopContinuous = (0, react_1.useCallback)(function () {
        setContinuousMode(false);
        continuousModeRef.current = false;
        processingRef.current = false;
        stopRecorder();
        stopConversation();
        cancelSpeech();
        setVoiceState('idle');
    }, [stopRecorder, stopConversation, cancelSpeech]);
    var toggleContinuous = (0, react_1.useCallback)(function () {
        if (continuousModeRef.current)
            stopContinuous();
        else
            startContinuous();
    }, [startContinuous, stopContinuous]);
    var speakProactive = (0, react_1.useCallback)(function (text, addToChat) {
        if (addToChat === void 0) { addToChat = true; }
        if (addToChat) {
            addChatMessage({
                id: "msg-".concat(Date.now()),
                role: 'assistant',
                content: text,
                timestamp: new Date().toISOString(),
                tags: ['proactive'],
            });
        }
        var wasContinuous = continuousModeRef.current;
        if (wasContinuous) {
            stopRecorder();
        }
        setVoiceState('speaking');
        speak(text, function () {
            if (wasContinuous)
                restartListening();
            else
                setVoiceState('idle');
        });
    }, [addChatMessage, stopRecorder, speak, restartListening]);
    var processTextInput = (0, react_1.useCallback)(function (text) {
        processingRef.current = true;
        processInput(text);
    }, [processInput]);
    return {
        voiceState: voiceState,
        continuousMode: continuousMode,
        isListening: isListening,
        isSpeaking: isSpeaking,
        transcript: transcript,
        speechError: speechError,
        sttSupported: sttSupported,
        ttsSupported: ttsSupported,
        startContinuous: startContinuous,
        stopContinuous: stopContinuous,
        toggleContinuous: toggleContinuous,
        processTextInput: processTextInput,
        speakProactive: speakProactive,
        cancelSpeech: cancelSpeech,
        connectionStatus: connectionStatus,
        liveResponse: liveResponse,
        assistantDraft: assistantDraft,
    };
}
