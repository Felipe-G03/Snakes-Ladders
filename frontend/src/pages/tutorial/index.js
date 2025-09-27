import React from 'react';
import { Link } from "react-router-dom";
import './style.css';

const Tutorial = () => {
    return (
        <>
            <div>
                <Link to="/" className="btn-back">Volte ao Jogo</Link>
                <h1>Tutorial</h1>
                <p>Bem-vindo ao tutorial do Jogo da Cobra e Escada! Aqui você aprenderá as regras básicas para jogar este clássico jogo de tabuleiro.</p>
                <h2>Regras do Jogo</h2>
                <ul>
                    <li>O jogo é jogado por dois ou mais jogadores.</li>
                    <li>Cada jogador começa na posição inicial (casa 1) e avança no tabuleiro de acordo com o resultado do dado.</li>
                    <li>Se um jogador cair na base de uma escada, ele sobe para o topo da escada.</li>
                    <li>Se um jogador cair na cabeça de uma cobra, ele desce para a cauda da cobra.</li>
                    <li>O primeiro jogador a alcançar a casa 100 vence o jogo.</li>
                </ul>
                <h2>Dicas para Jogar</h2>
                <ul>
                    <li>Planeje suas jogadas com cuidado e tente evitar as cobras.</li>
                    <li>Aproveite as escadas para avançar rapidamente no tabuleiro.</li>
                    <li>Divirta-se e jogue com amigos ou familiares!</li>
                </ul>
                <p>Agora que você conhece as regras básicas, está pronto para começar a jogar o Jogo da Cobra e Escada. Boa sorte!</p>
            </div>
        </>
    );
};

export default Tutorial;