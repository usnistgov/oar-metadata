package nist.oar.id;

/**
 * An exception indicating an attempt to use an ID that is syntactically 
 * invalid.  This may reflect a human transcription error. 
 */
public InvalidIDException extends NonexistentIDException {

    /**
     * create the exception  
     * @param id    the identifier that was misused
     * @param msg   the message explaining the misuse
     */
    public InvalidIDException(String id, String msg) {
        super(msg, id);
    }

    /**
     * create the exception
     */
    public InvalidIDException(String id) {
        super("ID is syntacticly invalid (transcription error?): "+id, id);
    }
}
