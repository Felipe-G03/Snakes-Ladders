import { Link } from "react-router-dom";
import './style.css';

const Reader = () => {
    return (
        <>
            <div class="body-reader">
                <div class="title">
                    <h1 class="h1_reader">Jogo da Cobra e Escada</h1>
                    <Link to="/tutorial" className="btn-tutorial">Tutorial</Link>
                </div>
            </div>
        </>
    );
};

export default Reader;