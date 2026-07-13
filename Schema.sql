CREATE TABLE IF NOT EXISTS `conversation` (
  `idConversation` int NOT NULL,
  `idPrompt` int DEFAULT NULL,
  `conversation` mediumtext,
  `conversationResponce` mediumtext,
  `conversationState` int NOT NULL DEFAULT '1',
  `conversationDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `isdeleted` bit(1) NOT NULL DEFAULT b'0',
  PRIMARY KEY (`idConversation`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `prompts` (
  `idPrompt` int NOT NULL,
  `prompts` mediumtext,
  `promptType` int NOT NULL DEFAULT '1',
  `promptDate` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `promptResponce` mediumtext,
  `isDeleted` bit(1) DEFAULT b'0',
  PRIMARY KEY (`idPrompt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS `users` (
  `idUser` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(150) NOT NULL UNIQUE,
  `passwordHash` VARCHAR(255) NOT NULL,
  `createdDate` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `isActive` BIT(1) NOT NULL DEFAULT b'1',
  PRIMARY KEY (`idUser`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
