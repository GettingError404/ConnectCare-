from pipeline.nlp_hybrid import NLPEngine
from pipeline.action_handler import ActionHandler
from pipeline.response_generator import ResponseGenerator
from pipeline.sentiment import SentimentAnalyzer

class ChatAgent:
    def __init__(self, config):
        self.nlp = NLPEngine(config["nlp"])
        self.actions = ActionHandler()
        self.response_gen = ResponseGenerator()
        self.sentiment = SentimentAnalyzer()

        # simple memory (upgrade later to Redis/DB)
        self.sessions = {}

    def process(self, user_id: str, message: str):
        # 1. Context
        context = self.sessions.get(user_id, [])

        # 2. NLP
        nlp_result = self.nlp.process(message)

        intent = nlp_result.get("intent")
        entities = nlp_result.get("entities", {})

        # 3. Sentiment
        sentiment = self.sentiment.analyze(message)

        # 4. Action execution
        action_result = self.actions.handle(intent, entities)

        # 5. Response generation
        response = self.response_gen.generate(
            intent=intent,
            action_result=action_result,
            sentiment=sentiment,
            context=context
        )

        # 6. Update memory
        context.append({"user": message, "bot": response})
        self.sessions[user_id] = context[-10:]  # keep last 10

        return {
            "response": response,
            "intent": intent,
            "sentiment": sentiment,
            "action_data": action_result
        }