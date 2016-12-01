package nist.oar.id;

/**
 * An exception indicating an attempt to use an ID that is not registered 
 * is otherwise does not exist.
 */
public NonexistentIDException extends IDException {

    /**
     * create the exception  
     * @param id    the identifier that was misused
     * @param msg   the message explaining the misuse
     */
    public NonexistentIDException(String id, String msg) {
        super(msg, id);
    }

    /**
     * create the exception
     */
    public NonexistentIDException(String id) {
        super("ID does not exist: "+id, id);
    }
}
