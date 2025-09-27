import React from 'react';
import Tabuleiro  from '../../components/tabuleiro';
import Reader from '../../components/reader';
import './style.css';


const Game = () => {
    return (
        <>
            <Reader />
            <div class="Game">
                <Tabuleiro />
                {/* <Dado /> */}
            </div>
        </>
    );
};

export default Game;